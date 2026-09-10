<!-- CURRENT_STATE_HISTORY_BOUNDARY: requirement-1 -->
> **Current code/readiness summary (reviewed 2026-09-07): [CURRENT_STATE.md](CURRENT_STATE.md).**
> This file retains dated technical notes and historical observations below.
> Older phrases such as "current", "not implemented", "next" or "passed" describe
> their recorded checkpoint, not today's code, database, freshness or permissions.
> File A remains plan authority. Historical counts never grant runtime activation.

## 2026-09-10 - PR #6 local repair and controlled 03D recovery

Local changes based on PR head `6de1e14973edcf62b61c9b6a1441214ace656ec4`
repair the three supplied CI failures and add the requested controlled
supersession/crash/concurrency acceptance. E1 and its link remain preserved;
deterministic E2 and immutable review evidence own the corrected retention
proof. Already APPLIED pre-fix semantic history requires migration review.
Concurrent finalization/registration is idempotent, late failures cannot undo
APPLIED, and stored payloads must match their indexed ID/version.

The existing explicit R18 schema owner adds `r18_retention_supersessions` and
guards. This has only been applied to scratch databases. See the implementation,
test-first findings and operator boundary in
[the execution record](fable/RHIST03D_PR6_REPAIR_2026-09-10.md).
Final local regression: **1699 passed, zero failures/skips, one warning**;
compile, Ruff and frontend pass. Mypy remains at 512 legacy errors in 70 files,
with zero new normalized diagnostics versus actual 03C source. Commit/push and
exact-head CI after this repair remain pending. 03D is IN PROGRESS, 03E/03F remain LOCKED, and
LIVE-DATA-VERIFIED / PRODUCTION-ACCEPTED remain NO. No authority ceiling changed.

## 2026-09-09 - R-HIST-03C outcomes and revision retention

Implemented on the existing `feat/rhist03-producer-wiring` branch / PR #6,
continuing `R-HIST-03_PRODUCER_WIRING_BUILD_PLAN.md`; no replacement architecture.

- `r16_retention.py` connects the existing PIT write paths to the existing
  retention publication/outbox/authority. Frozen hypotheses require the exact
  S8 publication, version, lineage hash and full persisted-payload SHA-256.
  Original decision inputs are validated against the parent's protected raw
  object roots, including normalized OHLCV; newer or corrected bars cannot leak
  into an earlier hypothesis.
- Outcomes preserve the original hypothesis hash and their own observation
  time/path evidence. Explicit revisions preserve exact predecessor hashes;
  source corrections, outcome changes and interpretation/rebuild versions
  append without UPDATE/DELETE of historical artifact values. SQL triggers
  enforce immutability, and replay remains idempotent.
- Artifact rows, immutable links and retention intent enter the same SQLite
  transaction. Post-commit failure leaves hidden, replayable rows. Governed
  readers validate PUBLISHED proof, authority references and evidence bytes;
  GET/read paths never create retention intent or backfill legacy history.
- All hypothesis states remain represented, with separate no-entry, expired,
  censored, data-gap and ambiguous outcomes. Intrabar target/stop ambiguity is
  excluded from definite win/loss statistics rather than learned as a loss.
  CONFIRMED history does not grant confirmation or execution authority.

The additive migration is `0023_r16_outcome_revision_retention`. Apply it only
through the existing explicitly approved producer/admin command, targeting the
existing research database (substitute its actual path):

```sh
cd backend
python -m trendforge_api.cli r16-schema --db-path /path/to/research.sqlite --apply
```

Keep the existing canonical market-data location configured, including
`TRENDFORGE_MARKET_DATA_DB_PATH` when it is separate. Every inherited root must
resolve exactly; there is no latest-data fallback. Newly published S8 artifacts
carry the full payload seal. Older S8 publications without that seal remain
unchanged but cannot parent a new governed R16 freeze. Existing unprotected R16
rows likewise remain in storage but are not exposed as governed history. Do not
silently stamp present-day hashes onto those older rows; verified historical
repair requires a separate explicit operation.

Tests were added and observed failing before the safety implementation. Local
commands/results, including the Mypy baseline comparison, are in VALIDATION.
The final exact-head CI evidence is recorded on PR #6, not inferred from local
results or an older green head. No merge is part of this checkpoint.

Remaining order: 03D frozen ML/model/profile/audit producers, 03E registry and
100% coverage/reconciliation, 03F complete concurrency/crash/golden acceptance,
then FULL R-HIST-03 gate, then R-HIST-04 archival. None of those stages is marked
implemented here. LIVE-DATA-VERIFIED: NO. PRODUCTION-ACCEPTED: NO.

## 2026-09-07 - Atomic research snapshot (next requirement)

The selection refresh now reads `GET /api/v1/selection/snapshot` instead of
22 independent latest endpoints. A request-scoped read-only SQLite transaction
pins the existing research, canonical market-data and macro-context readers.
R1/R2 and downstream identity/hash mismatches cannot be mixed. One S8-service
assembly supplies core panels; pipes and quantities reuse its outputs. Four
existing dependent context rooms also travel in the envelope, for 26 named
panels with individual unavailable reasons, one response identity and checksum.

The old selection-ready listeners no longer start independent latest reads in
the main terminal. The browser validates the entire envelope before rendering
and rejects late overlapping responses. Source decision time, captured database
view time and current gate evaluation time are distinct. S8 projections returned
by this GET are explicitly NOT saved; History remains a separate read-only view.

The existing R2-B observation assessment is recorded on the cash post-commit
WRITE path before S8, not by the new GET. It retains the same named-source proof
rules and matching input checks. Missing or obsolete activation evidence is not
promoted. No new source downloader, database, migration or broker authority.

Observed local checks: 43 focused backend tests passed; full frontend command
passed with 220/220 acceptance checks plus the existing/new Node suites; Python
compilation and whitespace checks passed. Local Chromium navigation was blocked
by the execution environment, not recorded as a browser pass. Pinned full-suite,
lint and browser CI results must be recorded after observation.
See [ATOMIC_RESEARCH_SNAPSHOT.md](ATOMIC_RESEARCH_SNAPSHOT.md) for the contract.

## 2026-09-07 - Requirement 1: current state versus history

Added the current-state summary, separate UI provenance axes and isolated saved
S8 history viewer. R5 v2 is accepted by the existing display adapter. Missing S7/S8
responses clear old panels; failures, original snapshot times and UNKNOWN statuses
remain visible. No backend gate, model approval, migration or execution change.
Observed commands and limitations: [REQUIREMENT_1_VERIFICATION.md](REQUIREMENT_1_VERIFICATION.md).

## Historical checkpoints (preserved)

## 2026-09-02 - CROSS-004 / TDG-GAP-014 named strategy-source contracts

`selection/profile_source_contracts.py` now owns one canonical, read-only
source dependency registry for PRF-001 through PRF-007. Every profile lists
exact mandatory, confirmation and veto source groups with ALL_OF/ANY_OF
policy, evidence family, registration coverage, delayed-context status and
live-data requirement. Registration is explicitly separate from freshness,
usable rows, lineage, source activation and confirmation.

`GET /api/v1/selection/profile-source-contracts` returned HTTP 200 with seven
profiles and zero activation, confirmation or execution authority. PRF-001
and PRF-002 correctly report `openalgo_intraday_candles` missing and remain at
WAIT without verified live bars. Delayed AMFI, CFTC, EIA, WGC, weather and crop
sources remain confirmation/context groups, never mandatory intraday proof.

Verification: focused 5 passed; complete backend 1,458 passed with one existing
deprecation warning; Python compilation passed; frontend 219/219 passed.

## 2026-09-02 - R0-C compiler-derived quarantine and API

R0-C now has a first-class, compiler-derived quarantine contract in
`backend/trendforge_api/source_cohort_r0c.py`. It partitions every compiled
source contract outside the six-key R0-B cohort and forces every remainder to
stay unreviewed, quarantined, non-voting, non-confirming and non-executable.
The builder fails closed on duplicate contract IDs, an incomplete R0-B/R0-C
partition, or any unexpected R0-C gate permission.

`GET /api/source-inventory/r0c-cohort` exposes the same hash-scoped partition
read-only. It is not a second registry and does not change source activation.
Runtime observation returned HTTP 200 with a complete partition, zero reviewed
members, zero gate-authorized sources and every member quarantined.

Verification: focused R0-C 4 passed; complete backend 1,453 passed with one
existing deprecation warning; frontend 219/219 passed.

R0-C quarantine acceptance is complete. R0 remains PARTIAL because
source-specific proofs, maturity transition history, unresolved mirror/resolver
values and activation review remain separate work.

## 2026-09-02 - R18 model governance fixture implementation

R18-A through R18-E are implemented at the honest MODEL_NOT_APPROVED ceiling.

- r18_governance.py owns champion/challenger states, dataset/feature/formula/model hashes, PIT-only fold and holdout validation, cost-aware Brier/ECE/net-R evaluation, R16-storage-proven evaluation, immutable persisted review evidence, SHA-256 chain review records, feature/prediction/calibration drift, automatic demotion and deterministic rollback identity.
- r18_store.py owns explicit migration 0014 and append-only model, evaluation, promotion-review and drift tables. The migration code is built and fixture-tested but was not applied to the live database.
- GET /api/research/ml/governance is read-only. POST /api/research/ml/reviews records a human governance review only and cannot reach broker/order code. APPROVE fails while R16 is PIT_NOT_APPROVED.
- frontend/r18-model-governance.js is mounted in the existing Paper/ML panel. It shows model/PIT/schema state, dataset age, blockers and governance history while hiding probability, win rate and performance.
- Runtime observation: HTTP 200, MODEL_NOT_APPROVED, PIT_NOT_APPROVED, BUILDING, dataset age 5 days, WAIT_R18_SCHEMA_NOT_APPLIED, zero governance records and executionAuthorized=false.

Verification: R18 focused 14 passed; complete backend 1,449 passed; Python compilation passed; frontend 219/219; dedicated R18 and full npm tests passed.

R18 code/fixture acceptance is complete. Production model promotion is not complete until migration 0014 is separately approved/applied and R16 passes PIT/OOS approval.

## 2026-09-01 - Documentation-reconciled build checkpoint

Current code and recorded verification establish one build boundary:

- R1/R2 and WAIT-only R3 are implemented; R3 consumes hash-matched R1/R2 evidence and cannot create CONFIRMED or trade geometry.
- R4-R8 and R10-R16 are implemented at their documented research ceilings. R9 remains postponed.
- R14's corporate-action join is implemented and required by R5; missing or conflicting terms fail closed.
- R16 storage, replay, labels, metrics and read-only UI/API are implemented, but the real dataset has only one complete S8 date. Runtime remains BUILDING / PIT_NOT_APPROVED.
- R17-B-F/H/I are fixture-verified. R17-G is POSTPONED_BY_USER after no usable quote, replay or stream.
- R18 code is not present. R18-A is next; MODEL_NOT_APPROVED remains mandatory.

This corrects stale navigation text and adds no runtime behavior.

## 2026-09-01 - R17-G deferred; R18-A is the next active build

The user chose not to renew the Kite session now. R17-G is therefore
`POSTPONED_BY_USER`, not complete and not failed implementation. R17-B through
R17-F and R17-H/I remain built and fixture-verified. The approved live attempt
resolved 10/10 exact NSE equities, observed populated OpenAlgo intervals, found
and fixed TrendForge's missing `60m` token, and then failed closed when the
first RELIANCE quote returned `Incorrect api_key or access_token`.

OpenAlgo remains optional, read-only, disabled as a TrendForge data authority
and non-executable. `REST_SHADOW_OBSERVED`, `STREAM_SHADOW_OBSERVED` and
`SHADOW_LIVE` remain unclaimed. R9 ORB/VWAP stays postponed with the missing
verified intraday-bar prerequisite.

Current verified regression evidence remains:

    Interval/REST focused:          25 passed
    Focused R17/OpenAlgo safety:   132 passed, 1 deprecation warning
    Complete backend:            1,435 passed, 1 deprecation warning
    Frontend acceptance:           218/218 plus R17 shadow check

The next active coding milestone is R18-A model-governance foundation. It may
build versioned champion/challenger contracts, fail-closed evaluation,
human-only promotion, drift demotion, rollback records and read-only
projections over the existing R16 PIT substrate. Runtime must remain
`MODEL_NOT_APPROVED`; R16 is still `PIT_NOT_APPROVED`, so probability,
performance, automatic promotion, execution and broker authority stay locked.
## 2026-09-01 - R17-G approved live observation blocked by expired Kite session

- The user approved the bounded, read-only local OpenAlgo observation. The
  existing `D:\openalgo` service started successfully on REST port 5000 and
  WebSocket port 8765; no OpenAlgo source file was edited.
- The real read-only `symtoken` master resolved all ten requested NSE equities
  exactly. The local intervals route returned a populated broker contract,
  including `60m`.
- TrendForge incorrectly omitted OpenAlgo's valid `60m` token and rejected the
  entire intervals response. `openalgo_client.py` now accepts `60m`; the
  existing provider-order test includes the observed token.
- After that repair, the first read-only RELIANCE quote failed closed. OpenAlgo
  returned HTTP 500 with `Incorrect api_key or access_token`; no populated
  quote, replay object or WebSocket market event was accepted.
- The bounded observer called no account, funds, holdings, positions, margin,
  tradebook or order route. It remained `BLOCKED / FIXTURE_VERIFIED`,
  `activationEligible=false`, `executable=false` and
  `STREAM_SEQUENCE_UNAVAILABLE`.

Observed verification:

    Interval/REST focused:          25 passed
    Focused R17/OpenAlgo safety:   132 passed, 1 deprecation warning
    Complete backend:            1,435 passed, 1 deprecation warning
    Exact identities:              10/10
    Local intervals:               HTTP 200, populated
    Local RELIANCE quote:           HTTP 500, no data, broker session invalid
    REST/stream activation:         not authorized by evidence

R17-G remains partial. The next external prerequisite is a fresh Kite login in
OpenAlgo. After that login, rerun the same bounded observer; do not change
TrendForge activation or OpenAlgo source code first.
## 2026-09-01 - R17-G OpenAlgo runtime preflight

The existing D:\openalgo\.venv successfully imported the TrendForge observer
and websocket-client 1.9.0. The real read-only symtoken master resolved the
bounded ten-symbol universe as 10/10 EXACT, 10/10 EQUITY and 10/10 populated
tokens. No service, credential, broker request or socket was opened. Live
observation remains approval-gated.
## 2026-08-31 - R17-G bounded observer built; live proof approval-blocked

- Added openalgo_live_probe.py, an explicit operator-run CLI that joins the
  existing R17 REST client, exact identity mapper, replay store and stream state
  manager. It does not auto-start, alter lane selection or create another
  downloader/database.
- The observer is loopback-only, accepts at most ten exact EXCHANGE:SYMBOL
  instruments, uses the provider server's symbols / Quote WebSocket contract,
  always closes sockets and reconnects once before resubscribing the same
  shortlist.
- REST calls are limited to the pinned read-only allowlist. The report stores no
  request body or credential and rejects account, funds, holdings, positions,
  margin, tradebook and order fields.
- The real D:\openalgo\db\openalgo.db master was read through SQLite mode=ro;
  NSE:RELIANCE resolved EXACT / EQUITY with populated token, lot size, tick
  size and mapping hash.
- Fixed a shared identity defect found by the new test: NSE cash symbols ending
  in CE, for example RELIANCE, are no longer mistaken for call options.
  Suffix-based derivative inference now applies only to NFO/MCX rows.
- The secret-free CLI observation with configuration deliberately absent
  returned BLOCKED / FIXTURE_VERIFIED and STREAM_SEQUENCE_UNAVAILABLE with no
  network request.

Observed verification:

    New R17-G observer tests:      11 passed
    Focused R17/OpenAlgo safety:   132 passed, 1 deprecation warning
    Complete backend:              1,435 passed, 1 deprecation warning
    Frontend acceptance:           218/218 + R17 shadow check passed
    Python compilation:            passed
    Real master identity:          NSE:RELIANCE = EXACT / EQUITY
    No-credential CLI:             BLOCKED / FIXTURE_VERIFIED

R17 remains PARTIAL. Starting D:\openalgo, decrypting its existing local API
key and using the current broker session for the bounded REST/WebSocket run
requires explicit informed approval. That action was not performed. Therefore
REST_SHADOW_OBSERVED, STREAM_SHADOW_OBSERVED, SHADOW_LIVE and production
readiness remain unclaimed.
## 2026-08-31 - R17-D-F and R17-H/I fixture closure

- Added exact, versioned NSE/NFO/MCX identity binding in
  `openalgo_identity.py`; unknown, ambiguous, expired and cross-segment rows
  fail closed to `WAIT_IDENTITY`.
- Added deterministic raw/normalized replay in `openalgo_replay.py`, reusing
  the existing content-addressed store and last-good rules. No database or
  downloader was added.
- Added the dependency-free stream integrity state machine in
  `openalgo_stream.py`: authentication, subscription, heartbeat, bounded
  queues, duplicate/reorder handling, reconnect and explicit
  `STREAM_SEQUENCE_UNAVAILABLE`.
- Added `openalgo_shadow.py` and read-only GET
  `/api/v1/integrations/openalgo/shadow`. It preserves every base R1-R16 public
  state, emits zero confirmations and remains `executable=false`.
- Added seven purpose-specific option views (PCR, OI walls, max pain, IV,
  Black-76 Greeks, liquidity and unsigned gamma). Every view carries the same
  snapshot/root lineage when derived from one chain; concentration reports
  zero independent confirmations.
- Corrected research quantity to include declared per-unit cost and removed
  lot-size double multiplication from notional/funds calculations.
- Replaced the unsafe `configured => SHADOW_LIVE` shortcut. Configuration now
  stops at `FIXTURE_VERIFIED`, so a requested OpenAlgo lane remains
  `FREE_OFFICIAL` until observed REST/stream/replay proof passes.
- Added the responsive OpenAlgo read-only shadow panel to Live Ops with compact
  values and a hidden lineage/formula inspector.

Observed verification:

```text
Focused R17/lane/security:   110 passed
Complete backend:            1,424 passed, 1 deprecation warning
Frontend acceptance:         218/218 + R17 shadow check passed
Python compilation:          passed
Disabled shadow GET:         DISABLED; rows=[]; executable=false
Configured-only shadow GET:  FIXTURE_VERIFIED; WAIT_REST_OBSERVATION
Configured-only data lane:   FREE_OFFICIAL; canConfirm=false
Shadow POST:                 405
```

R17 status remains **PARTIAL**. R17-G credentialed REST, shortlist,
WebSocket, reconnect and replay observation was not approved or performed.
The current secret-free local capability report is `ABSENT` with
`OPENALGO_CONFIGURATION_ABSENT`.
`REST_SHADOW_OBSERVED`, `STREAM_SHADOW_OBSERVED`, `SHADOW_LIVE`, broker
execution and production readiness are not claimed.

## 2026-08-31 - R17-C OpenAlgo REST client verified

- Repaired OpenAlgo history parsing for documented timezone-aware IST strings;
  canonical output is UTC ISO-8601. Numeric epochs remain accepted only when
  the JSON value is numeric, not a numeric string.
- Added strict read-only `ping`, `intervals`, `quote` and `multiquote` methods
  to the existing client. All eight allowlisted data routes are now
  `CLIENT_IMPLEMENTED`.
- History rejects valid-empty, malformed, non-finite, negative-volume,
  impossible-OHLC, duplicate and reversed fixtures.
- Quote/multiquote rejects missing fields, impossible geometry, stale/future
  timestamps when an age check is requested, partial results, error rows and
  exact symbol/exchange mismatches.
- Added per-route pacing, bounded transient retries, route-local circuit state,
  response-size enforcement and API-key redaction. No execution/account route,
  credential, dependency, migration or live broker request was added.

Observed verification:

```text
R17/OpenAlgo focused tests: 59 passed
Complete backend:           1,373 passed
Frontend acceptance:       218/218 passed
Python compilation:        passed
Fixture history timestamp: 2025-04-01T03:45:00+00:00
Fixture quote LTP:          101.0
Provider routes:            8/8 CLIENT_IMPLEMENTED
Contract hash:             8cff83dc22937cf69ac6240a30cfcadc6d5cfff2040b01696a9da31651e7a3b9
Executable:                false
```

R17 status: PARTIAL. R17-B and R17-C are complete. R17-D exact instrument
binding is next. Replay, stream fixtures, option-purpose votes and separately
approved live observation remain unbuilt; `SHADOW_LIVE` and production-ready
are not claimed.

## 2026-08-31 - R17-B OpenAlgo provider contract pinned

Historical checkpoint; the current route states and contract hash are in the
R17-C section above.

- Added `trendforge.openalgo-provider-contract.v1` to the existing OpenAlgo
  client boundary.
- Pinned local provider commit
  `24f8d395372799066a24ba1d6311f0e7791555d8`.
- Added read-only GET `/api/v1/integrations/openalgo/contract`.
- Pinned SHA-256 for eleven relevant route-registration, handler and WebSocket
  protocol files.
- Contract reports eight allowlisted POST data routes: four
  `CLIENT_IMPLEMENTED` and four `CONTRACT_PINNED`.
- WebSocket documentation/server variants and
  `STREAM_SEQUENCE_UNAVAILABLE` are explicit.
- No credential, network request, dependency, migration or stream was added.
- Current user authority retains non-executable research quantity and requires
  separate purpose-specific option votes in later R17-H.

Observed verification:

```text
R17/OpenAlgo focused tests: 31 passed
Complete backend:           1,348 passed
Frontend acceptance:       218/218 passed
Contract endpoint:         HTTP 200, executable=false
Contract hash:             be0f768d80a0b1dadf3b85721826659d92e5ca63820930c036f0de27ff10bbc4
```

R17 status: PARTIAL. R17-B is complete; REST repair/extension, identity,
replay, stream fixtures, option-purpose votes and conditional live observation
remain unbuilt.

## 2026-08-28 - Missing/WAIT decision-guide amendment (plan only)

File A section 25.27 is the mandatory pre-build contract for the pasted
Missing/WAIT completion plan. It now resolves per-side Top-10/15 semantics,
profile-scoped surveillance eligibility, separate intraday/swing geometry,
cost-adjusted research levels, one capped option-chain family, categorical
independent-family confluence, deterministic next/invalidation conditions,
MCX separation, immutable replay and runtime acceptance. Current code was not
changed. R12 remains PARTIAL / NOT READY; Elliott and options-dependent
decision approval remain blocked until the owning prerequisites pass.

# Build Status
## 2026-08-25 (R12) - Options walls/Greeks claims into S6

- New `selection/r12_options_claims.py`: mints OPTIONS_CONTEXT EvidenceClaims
  from validated options package (PCR, max-pain reference, GEX scenario).
  All claims share CG_OPTION_CHAIN correlation group, can_support_confirmed=False.
- Uses registered FTR IDs (FTR-023/024) from feature_registry — not invented
  FTR names. GEX labelled SCENARIO_ONLY_NOT_OBSERVED_POSITION.
- Tests: test_r12_options_claims.py 6 passed; full backend **1,226 passed /
  0 failed**; frontend 209/209.

## 2026-08-25 (S9 UI) - Historical prototype, superseded by R16 on 2026-08-28

This section records the retired prototype only. The current owner is
frontend/r16-pit-validation.js and the canonical authority fields are recorded
in the 2026-08-28 R16 checkpoint below.

- New `frontend/s9-pit-homework.js`: renders S9 PIT homework in the inspector
  Validation tab (`#s9PitHomeworkPanel`). Shows guidanceWinRate
  (WIN/(WIN+LOSS), CENSORED excluded from denominator, labelled "not a
  promise"), WIN/LOSS/CENSORED/NO_FORWARD_SESSION bar counts,
  PIT_APPROVED_FOR_GUIDANCE or PIT_NOT_APPROVED chip, per-symbol observation
  table (first 20). Copy: "Trade guidance — not a guaranteed win. Not an order."
- `#q5ValidationLock` replaced with live S9 status + sourceS8RunId.
- Adapter fetch count 16 (added `/api/v1/selection/pit-homework`).
- Acceptance-check additions: panel exists, script mounted with cache-bust,
  route referenced by adapter, guidanceWinRate + lock copy present, never
  assigns CONFIRMED, never calls place_order.
- Full backend 1,212 passed / 0 failed; frontend 209/209.

## 2026-08-25 - Production-research audit: PRODUCTION_RESEARCH_READY

## 2026-08-25 (dual-lane) - FREE vs OpenAlgo RO + research qty wired to UI

- Backend already landed: `selection/data_lane.py`, `selection/research_quantity.py`,
  `tests/test_dual_lane.py` (11), routes GET/POST `/api/v1/settings/data-lane`
  (preference only) and GET `/api/v1/selection/research-quantity` (POST 405).
  Default `FREE_OFFICIAL`. OPENALGO_RO only when env+capability pass.
  Qty at `draftConfirmedEligible`; `executable=false`; no orders.
- This follow-up **connects the shell** (was missing from the “certified” drop):
  `frontend/data-lane.js`, `frontend/research-quantity.js`; command-bar switch
  `#dataLaneSwitch` / `#dataLaneMeta`; `#researchQtyPanel` inside S7;
  `#researchFundsPanel` + `#researchPositionCard` in Live Ops; adapter 13→15
  fetches (`data-lane` + `research-quantity`) with matching `TrendForge*.apply`.
- Throwaways: `delete/gates_dual_lane_qty_2026-08-25/`.
- Live GET still honest: no official close on S7 card ⇒ most rows qty 0 /
  `WAIT_NO_STOP` until a closed last is passed in. Not CONFIRMED. Not OMS.

## 2026-08-25 (S8 ticket) - File A S8 persist-one-reconstructable-scan implemented

- New `selection/s8_persist_run.py`: ONE immutable blob per scan run —
  lineage ids for R1/R2/R14/R5/S2/S3/S4-pack/S5/S6/S7 (`WAIT_STAGE_ABSENT`
  when a stage has no run id), S2 weather block with suspect flags,
  S3 completeness tuple, rows = S7 idea cards ONLY (publicState copied,
  never re-scored; geometry null by model law), changeKinds vs prior
  comparable run (STATE/GATE/FAMILY/FEATURE + NO_BASELINE).
- Store: added `get_selection_payload` / `list_latest_selection_payloads`
  helpers (same tables; no new DB). STO-008 events written into the existing
  `selection_state_events` table with prior_state from prior run.
- Routes: GET `/api/v1/selection/scans{,/latest,/{run_id},/{run_id}/candidates
  [,/{symbol}]}`; POST ×2 → 405. `latest` builds+persists from the CURRENT
  hash-matched spine in one request.
- Fixed en route: `main._s8_from_current_spine` now runs the full same-request
  chain (pack→s5→s6→s7→blob) instead of passing an incomplete stage set.
- Post-review hardening: `s2_run_id` derived from CONTENT only
  (trading_date+regime+suspect flags — wall-clock excluded, dashboard
  refreshes no longer mint new runs); STO-008 baseline events use WAIT as the
  named starting state (never NULL-dropped); hybrid_pin validator rejects
  vote-shaped pins; store duplicate-run_id now raises ValueError instead of
  sqlite IntegrityError (all existing callers keyword-based, none catch
  IntegrityError); known limitation: payload + state-events commit on two
  connections (non-atomic; deferred to R16 migration approval).
- Tests: test_s8_persist_run.py **10 passed** (incl. P1 regressions); focused
  S7 regression 25 passed; full backend **1,190 passed / 0 failed**;
  frontend acceptance **201/201**.
- Live: `LIVE_S8_RECONSTRUCTABLE_WAIT_ONLY`; latest blob = 503 WAIT rows on
  current lineage; reconstruct-by-runId states match. CONFIRMED unreachable.

## 2026-08-25 - Production-research audit: PRODUCTION_RESEARCH_READY

- Full backend pytest: **failed=0** — 1,180 passed (delete/gates_prod_audit_2026-08-25/pytest_full_after.txt).
- Frontend acceptance: 197/197.
- Live GET battery on fresh :8000 uvicorn of this tree: 15 routes 200 /
  honest named-404 (`S7_SYMBOL_NOT_FOUND` for off-shortlist symbol probe);
  confirmedCount=0 everywhere present; POST ×3 → 405; `ACTIVATION_FALSE`.
- Six historical failures FIXED as STALE_FIXTURE (assertions untouched):
  market_data_service ×3 + fno_ban + vyom resolver = fake transports lagged
  production's `trading_date=` kwarg; hybrid overlay empty-DB test now
  isolates storage to tmp_path (real dev DB gained live R1/R2 payloads).
- Safety grep: usage-level scan SELECTION_CLEAN; guard doc-mentions required
  and present. One public-state owner: S7. No qty/win%/broker anywhere.

## 2026-08-24 (night) - File A S7 state gates (SEL-008) implemented [concurrent session]

- New `selection/s7_state_gates.py`: PRF-003-SWING-EOD live profile
  (STRUCTURE required; PARTICIPATION/EVENT/RS-companion alternative via
  `PRF003_RS_AS_COMPANION`; weather + event-blackout fail-closed flags).
  One public-state owner: All Stocks / idea cards project S7 only.
  `draftConfirmedEligible` computed per §10.4 shape; never published as
  CONFIRMED (row+batch validators). Geometry keys null by model law.
- Routes: GET `/api/v1/selection/s7-state{,/{symbol}}`; POST 405.
  S6 route now attaches live S2 weather context (`market_context`).
  Legacy `/selection/resolution` RETAINED read-only for the M-Factor BFF
  subsume-check (matches the audit-round entry below; UI never reads it).
- Fixed en route: `s5_shortlist_enrichment` read nonexistent
  `FoEnrichmentRow.oi_quadrant/oi_change` — real fields live on the
  `near_future` contract slice (AttributeError killed the live route).
- Tests: test_s7_state_gates.py 12 passed; focused cross-suite green;
  full backend **1,174 passed / same 6 failures** at this entry's snapshot;
  frontend **197/197**; live isolated-port probe: `LIVE_LOCKED`, POST 405.
  (Counts are point-in-time; see newer entries below for later snapshots.)

## 2026-08-24 (audit round) - one family-resolution board: /s6-resolution merges cash + structure claims, bounded to S5 shortlist

- `selection/s6_family_resolution.py`: claim feed is now `merged_feed` — the
  cash FTR-040 adapter (`claims_from_cash_pipeline`) unioned with R5-published
  structure claims. Cash + RVOL share CG_ACTIVITY_SESSION so the merged feed
  keeps exactly ONE participation representative per symbol (strongest wins,
  others SUPPRESSED_CORRELATED and surfaced in whyUnknown).
- Rows are bounded to the S4/S5 structure-claimed shortlist
  (`bound_to_shortlist=True` default; wide diagnostics opt-out kept for tests).
  Claim-less rows no longer appear on the board.
- Cash-feed assembly is self-contained: identity from `latest_cash_identity()`,
  compiled contracts from `compile_default_inventory()`; any lineage ValueError
  degrades to a structure-only board with a CASH_FEED_* warning instead of 503
  (optional enrichment never blocks the board).
- Thin R3 `GET /api/v1/selection/resolution` is UNCHANGED (diagnostic, D-049);
  `/s6-resolution` is the family-resolution board. Decision D-050.
- Tests: s6 suite 14 passed (adds bounding + injected-feed + real pipeline
  assembly tests); combined regression 69 passed; full backend suite
  1162 passed / same 6 pre-existing unrelated failures; frontend 193/193.

## 2026-08-24 (late) - File A S4 structure pack + S5 shortlist enrichment + S6 family resolution (WAIT ceiling)

- **S4 (SEL-005)** `selection/s4_structure_pack.py`: projects the persisted
  hash-matched R5 batch into a display pack (`trendforge.s4-structure-pack.v1`,
  ceiling `LIVE_S4_WAIT_REJECT_ONLY`). One CG_PRICE_STRUCTURE representative per
  row (breakout + same-root trend acceptance share the FTR-006 claim),
  CG_COMPRESSION NR stays max-WATCH, RVOL-EOD is a companion tag, pattern lane is
  display-only with `can_support_confirmed=false` enforced by model validation,
  WAIT_CA rows carry UNKNOWN codes instead of claims. Every WATCH/WAIT row has a
  non-empty `nextTrigger` / `invalidationCondition`; no entry/t1/t2 fields exist.
  Route: `GET /api/v1/selection/s4-structure` (POST 405); R5 `/structure`
  refactored onto the shared hash-matched guard. Frontend: `s4-structure.js`
  paints Structure Lab + Live Ops; All Stocks shows S4 tags + next trigger via
  the extended adapter/product-fixture while geometry stays "NONE — R5 research,
  not a trade".
- **S5 (SEL-006)** `selection/s5_shortlist_enrichment.py`: bounded enrichment of
  ONLY the S4 structure-claimed shortlist (`trendforge.s5-enrichment.v1`, ceiling
  `LIVE_S5_ENRICH_WAIT_ONLY`). Fallback (pack missing) = R2 WATCH ∩ latest R5
  setups, never bare WATCH-40. Reuses r6 loaders and radar recipes: delivery z is
  EOD-only (FORBIDDEN_ON_INTRADAY guard), one FO OI package per A6, OPTIONS_PACKAGE
  pinned to `UNKNOWN_NEEDS_R12` with score 0 (cash-only never punished), unnamed
  deals never labelled FII, `nse_fii_dii` stays a MARKET_WIDE_NOT_PER_STOCK chip,
  `shpFiiDelta=null`, AMFI labelled delayed. Route:
  `GET /api/v1/selection/s5-enrichment` (POST 405). Frontend: `s5-enrichment.js`
  honest-unknown chips on All Stocks + Live Ops; adapter fetch list extended in
  lockstep with its name list.
- **S6 (SEL-007)** `selection/s6_family_resolution.py`: resolves lineage-backed
  claims through the canonical `resolver.resolve_evidence` using the ACTIVE
  VERSIONED PROFILE OBJECT (required families are read from it, never hardcoded).
  Emits per-symbol family support/oppose map, conflict flag,
  `evidenceStrength` labelled "Evidence strength - not win probability",
  missingFamilies, researchState WAIT/WATCH/REJECT, `canUnlockConfirmed=false`.
  S5 typed fields are projected as context notes, not votes; S2 weather attaches
  as display-only market context. Route: `GET /api/v1/selection/s6-resolution`
  (POST 405). Frontend: `s6-resolution.js` Decision view (support/oppose/missing)
  inside the Evidence Inspector plus Live Ops research records appended to the
  live decision list. NOT S7, NOT CONFIRMED, NOT Combined_Score.
- Tests: see VALIDATION.md 2026-08-24 entries.

## 2026-08-24 (evening) - S6 claim-feed widening: R5 claims published + merged feed

- `selection/r5_live.py`: R5StructureRowV1 now carries the real minted
  `claims` + backing `facts` (additive fields, default empty). Row validator
  rejects any confirming claim at the boundary; old payloads without the
  fields still load. SCHEMA v1→v2 / PROFILE_VERSION 1.0.0→1.1.0: run_hash
  widens across this deploy boundary (deterministic per version).
- New `selection/s6_claim_feed.py`: collects R5-published structure claims,
  unions them with the FTR-040 cash feed (`merged_feed`), and projects S2
  weather as a display-only `market_context` block
  (`canSupportConfirmed=false`) attachable to the resolution DTO
  (`R3ResolutionV1.market_context`, additive).
- Callers opt in; no route behavior changed this ticket. Closes overlay-map
  pipe-gap #5 at the ingestion layer and gives #1 its display half; gate-math
  wiring stays with profiles/R2-B.
- Tests: new tests/test_s6_claim_feed.py 4 passed; focused r5/resolver/r1
  suites green; full backend **1,127 passed / 6 failed (same six)**;
  frontend acceptance 186/186.

## 2026-08-24 - File A S3 cheap discovery implemented

- Added `selection/s3_cheap_discovery.py` and read-only GET routes
  `/api/v1/selection/cheap-discovery` and `/watch`; POST returns 405.
- S3 consumes current A3/R2 lineage, scans the complete dynamic R2 universe,
  preserves R2 order, and records eligible/scanned/excluded/failed/unattempted
  counts plus completeness. Partial scans fail closed to WAIT.
- Cheap evidence includes pre-open/activity/OI/event presence and PIT EOD
  RVOL/NR7/RS where authoritative inputs exist. Missing inputs remain UNKNOWN.
  Cash-only missing OI is not penalized. Official event presence is not treated
  as deal direction or FII activity.
- Delivery is never queried; no second ranker or volume vote was added;
  `sourceActivationReady=false`, `confirmedCount=0`, ceiling
  `LIVE_S3_WATCH_WAIT_ONLY`.
- Added compact frontend queues in All Stocks and Live Ops. No win probability,
  entry, target, stop or executable quantity is shown.
- Runtime observation: 2,633 eligible/scanned, completeness 1.0, 0 failed,
  0 unattempted, 1,824 WATCH candidates, 0 CONFIRMED. Full batch ~3.1s after
  replacing per-symbol A4 reads with one symbol-set query.
- Verification: focused S3 10 passed; related backend 76 passed; frontend
  186/186; complete backend 1,123 passed and 6 unrelated pre-existing failures.
  TrendForge is not production-ready while those failures remain.

## 2026-08-22 (later) - File A S2 market weather finished

- Parser fix parsers/nse_index_close_parser.py: points-as-percent killed;
  provenance field changePercentStatus on every row; strict optional floats.
- New selection/s2_market_weather.py + routes GET /selection/market-weather{,/sectors},
  POST 405. Breadth UNKNOWN when no official snapshot (never 0/0). VIX band
  LOW/NORMAL/HIGH level context only. Commodity: local MCX % vs grey CFTC/WGC
  (canDirectContract=false).
- Tests: s2 suite 10 passed (live-leak regression added); combined spine+s2 94 passed; frontend 181/181. Live check: stored stale parse fails closed to INDEX_PCT_STALE_PARSE_SUSPECT until next refresh.
# Build Status
## 2026-08-23 - Current File A R1-R14 reconciliation

This checkpoint supersedes the older consolidated table at lines 1407-1425;
that table is retained as historical evidence. Current code, focused tests and
read-only runtime observation show:

| File A step | Current status | Usable scope |
|---|---|---|
| R1 | IMPLEMENTED | Persisted 123-source disposition bundle and 2,633 stock evidence rows; research only |
| R2 | IMPLEMENTED | 2,633-row cash attention order (1,824 WATCH, 809 WAIT); no CONFIRMED |
| R3 | IMPLEMENTED | Hash-scoped family resolver; all 2,633 current rows remain WAIT |
| R4 | IMPLEMENTED | A2 identity pin plus pinned PK inventory; unknown/companion IDs fail closed; PK has zero vote |
| R5 | IMPLEMENTED | Adjusted closed-bar breakout/NR/RVOL structure; live ceiling WATCH/WAIT/REJECT and zero CONFIRMED |
| R6 | IMPLEMENTED AT BOUNDED RESEARCH CEILING | Top-40 shortlist stickers and top-10 display; no rank/state override or confirmation |
| R7 | IMPLEMENTED OFFLINE ONLY | Finite PK JSON worker/differential harness; developer comparison, no production API or vote |
| R8 | IMPLEMENTED / GUIDANCE ONLY | Versioned native scanner registry and native-core guidance API; zero confirmation |
| R9 | SKIPPED / NOT IMPLEMENTED | Operator-deferred ORB/VWAP until verified intraday bars exist |
| R10 | IMPLEMENTED / ZERO CLAIMS | Versioned pipe DSL over native-core matches; no vote or confirmation |
| R11 | PARTIAL / NOT READY | Swing/MCX contracts and fixtures exist; full local MCX master/profile vertical is incomplete |
| R12 | PARTIAL / NOT READY | Options-domain/pricing components exist; shortlist PIT timeline/walls API is incomplete |
| R13 | IMPLEMENTED / GUIDANCE ONLY | Six formula-pinned scanners over adjusted PIT closed EOD bars; zero claims/state/rank mutation |
| R14 | IMPLEMENTED AT WAIT-ONLY CEILING | Official CA/identity-continuity join feeds R5; unresolved/conflicting CA remains WAIT |

### Source routing through R4 and R5

| Inventory scope | R4 use | R5 use | Preservation rule |
|---|---|---|---|
| 123 registry jobs | R1 preserves every job disposition; R4 reads the R1/R2 spine and adds identity/PK tags only | Official adjusted cash bars, corporate-action join and index companion provide structure inputs | Sources not applicable to R4/R5 remain visible in R1 clocks, lineage and missing-evidence records; they are not deleted |
| Aliases/companions | Never independent identity or votes | Never extra structure votes | Share their canonical dataset root and cannot inflate evidence |
| News, options, macro, FII/FPI, commodity and delayed sources | Skip as R4 voters | Skip as R5 structure voters | Retained for R1 health and later source-specific milestones, especially R6/R11/R12 |

This does **not** mean all 123 jobs vote in R4 or R5. Flattening different
grains into one score would double-count evidence and mislabel delayed/context
data. The app is ready for research inspection at the stated ceilings, not for
production trading, quantity, broker orders or live CONFIRMED.
Current complete regression: backend 1,096 passed / 6 failed / 1 warning;
frontend 176/176 passed. The six backend failures prevent a production-ready
claim even though the focused R1-R6/R14 suite passed 111 tests.

## 2026-08-23 - M-Factor usefulness: R5 STRUCTURE claims wired into FUS-009

Ticket: `docs/fable/remaining_build/M_FACTOR_USEFUL_FUS009_WIRING_GLM_PROMPT.md`.

- **`selection/m_factor_claims.py` (new):** `rebuild_r5_claims` re-runs the
  same deterministic `analyze_closed_bar_structure` (FTR-006 / FTR-007 /
  FTR-017) that minted the hash-matched persisted R5 row; any drift withholds
  claims with `WAIT_R5_REBUILD_DRIFT`. `merge_symbol_claims` concatenates the
  FTR-040 cash claim (FTR-017 shares CG_ACTIVITY_SESSION, so FUS-009 takes the
  group max - no double count). `index_session_conflict` (INDEX_CONFLICT_V0,
  +/-1.0% session heuristic) refuses values beyond a +/-7% sanity bound: the
  live A5 `nifty50_change_percent` was **20.15** (impossible parser artifact),
  so the flag stays unproven and a `INDEX_CHANGE_SUSPECT` warning is shown.
  A conflict seats WAIT; it never creates an opposite trade. Rebuilt claims
  keep `can_support_confirmed=False`; the R5 WAIT ceiling is untouched.
- **`m_factor_bff.py`:** consumes the merged claim set. **Dropped the per-row
  equality against persisted R3** (that check was only valid while M-Factor
  used R3's thin claim set). FMR-010.1 now means: long/short equal the BFF's
  own two `resolve_evidence` runs; persisted R3 stays a lower bound plus a new
  per-row `r3EvidenceStrength` debug comparison. `readiness=SETUP_READY` only
  when the STRUCTURE family actually voted support (not a setups string).
  `how` cites FTR/claim IDs or a named withhold code; `what` is
  NAMED_DEAL/DEAL_UNNAMED_OR_UNALIGNED/UNKNOWN_NO_LARGE_DEAL_ROW from R6
  (labels only - FTR-026 EVENT fact wiring is not live, no EVENT vote).
  R1 restriction VETO seats WAIT (`SAFETY_BAN_VETO`). R14 stale vs the R5
  build withholds all STRUCTURE claims. Geometry stays null; qty null;
  CONFIRMED impossible; other horizons stay empty with their WAIT codes.
- **Frontend:** `m-factor-live.js?v=20260823-mf4` fetches `debug=1` and
  renders the selected row's FUS-009 family bars (S_f/O_f + weights + R3
  comparison) on its card; BUY and SELL cards from the DTO.
- **Live result (tradingDate 2026-08-21, universe 2633):** boards
  **BUY 40 / SELL 40 / WAIT 40** (was BUY 40 flat ~24.9 / SELL 0).
  Rank is now real tiers: 0 (no claims) / ~11-25 (participation only) /
  50.7-55.0 (accepted FTR-006 + participation; STRUCTURE 0.30 + PARTICIPATION
  0.25). BUY top-40 band 54.75-55.0 - saturation is the File-A binary
  FTR-006 accept (strength 1.0 by law), not a fudged curve. 95 of 120 capped
  rows are SETUP_READY on real STRUCTURE votes. Example SELL: AADHARHFC
  long 0 / short 55 (Bear). Cold build ~16.5s (R5 rebuild for hundreds of
  setup rows), cached ~5ms for 10 minutes (TTL raised from 30s on 2026-08-23:
  EOD lineage changes only on a new pipeline run and the batch carries its
  own runId/availableAt, so a 10-minute-old composition stays honest).
- **Tests:** `test_m_factor_claims.py` 9 passed (golden determinism, FTR-006
  lifts only the matching hypothesis, group max not sum, drift withhold,
  bearish short side, index sanity bound). `test_m_factor_bff.py` 17 passed
  (FMR-010.1 rewritten to the new contract; SETUP_READY-requires-structure
  added). Full backend suite **1071 passed / 6 failed** (the documented
  pre-existing set, one fewer than baseline). Frontend 176/176.

## 2026-08-22 - M-Factor live BFF + live tool room wiring

- **BFF:** `GET /api/v1/tools/m_factor` (read-only) in
  `backend/trendforge_api/selection/m_factor_bff.py`. Projects exactly two
  File A FUS-009 hypotheses per R2 row (BULLISH + BEARISH via
  `resolve_evidence`), verifies the row-direction recomputation equals the
  persisted R3 row, then exposes `longStrength/shortStrength/mBalance/
  rankStrength` in 0-100 display points and `M_FACTOR_CLASS_V0` bands.
- **Boards:** buy/sell/wait per horizon. swing is the only live path
  (EOD_RESEARCH). intra -> `WAIT_HORIZON_INTRADAY_NOT_ACTIVATED`,
  position -> `WAIT_HORIZON_POSITION_NOT_WIRED`,
  commodity -> `WAIT_HORIZON_COMMODITY_MCX_LOCAL_NOT_WIRED`, all with empty
  boards. No second score, no Combined_Score, no geometry (entry/stop/t1/t2/
  quantity stay null), no CONFIRMED, `sourceActivationReady=false`.
- **Fail-closed:** 503 `WAIT_MIXED_SNAPSHOT`/`R3_RESOLUTION_NOT_READY`/
  `WAIT_R1_BUNDLE_NOT_READY`/`WAIT_R2_ATTENTION_NOT_READY` on lineage
  problems; POST is 405. Readiness maps from R5 (SETUP_READY only with real
  detected closed-bar setups) and R3 REJECT (INVALIDATED).
- **Frontend:** `frontend/m-factor-live.js` owns the m_factor tool room
  through a small delegation hook in `product-fixture.js` (`renderTool`).
  Live hero (real run id + IST cutoff), horizon/side switcher, market strip,
  evidence bars, rank table, stock decision panels (BUY/SELL research
  direction, PENDING levels, how/what/where/when), gate-filled validation
  layers, locked `PIT_NOT_VALIDATED` track (sample 0) and the engine
  ownership table. On 503/network error it paints the typed WAIT code and
  never falls back to fixture cards.
- **Repair (2026-08-22 evening, "still old data" report):** the browser was
  serving a stale cached `product-fixture.js`/`m-factor-live.js` because the
  edited files kept their old `?v=` cache-busters. Bumped to
  `?v=20260822-mf2`, and `m-factor-live.js` now marks its output
  (`data-mf-live`) with a MutationObserver that reclaims `#toolContent` if a
  stale painter overwrites it while m_factor is active. BFF latency over the
  2633-row universe (~7s cold: loaders ~3.8s + compile ~0.8s + resolver runs)
  got a 30s lineage TTL + per-lineage batch cache (disabled under pytest so
  loader monkeypatches stay authoritative) and an lru_cache for the compiled
  inventory: cold 6.8s, cached ~5ms, intra ~8ms.
- **Repair:** fixed pre-existing broken relative import
  `evidence_radar/boards.py` (`..fii_stock_signals` -> `...fii_stock_signals`)
  that made the whole backend suite fail collection.
- **Tests:** `backend/tests/test_m_factor_bff.py` 16 passed (FMR-010.1
  equality vs `/api/v1/selection/resolution`, band boundaries, board rules,
  horizon fail-closed, track lock, 405, 503 mixed hashes, no fixture values,
  debug family weights). Frontend acceptance-check 175/175.
- Full backend suite 2026-08-22: 1051 passed / 7 failed; the 7 are the
  pre-existing baseline failures (hybrid overlay empty-DB isolation,
  evidence-radar cross-test pollution, market_data_service fixtures, VYOM,
  fno-ban clamp) and predate this milestone; see docs/VALIDATION.md.

## 2026-08-15 - A5/A6/C0/B/C1 cash research stack

- **A5:** Index last-good parsed as context (NIFTY 50 / INDIA VIX). Unresolved
  CA demotes WATCH to WAIT. Index cannot rank or confirm.
- **A6:** F&O enrichment on WATCH shortlist only. Futures OI never mixes with
  option OI. Cash-only names are `NOT_REQUIRED`, not failed.
- **C0:** Generated use matrix. `can_rank`/`can_veto`/`can_unlock_confirmed`
  live here. R0-B `canVote` stays false. Activation stays false.
- **B:** MWPL missing/unproven stays `MWPL_MISSING` and does not block cash.
- **C1:** Attention rank only if C0 `can_rank` for cash. Conflict or CA WAIT
  is not ranked. No CONFIRMED.
- Tests: `test_cash_a5_c1.py` 5 passed. A1â€“C1 suite 19 passed.

## 2026-08-15 - A4 PIT cash history vintages

- Persist immutable RAW cash session bars. A changed hash for the same
  instrument/date cannot overwrite.
- CA vintages store factor, effective date, `available_at` and revision.
  Replay hides vintages with `available_at` after `decision_at`.
- Visible resolved CA opens a new ADJUSTED series id (CROSS-020). Unresolved
  CA is `WAIT_CA`, not bullish. Baselines need at least two visible sessions.
- `can_rank=false`. Routes: `POST/GET /api/v1/selection/cash-history/*`.
- Tests: `test_cash_a4_history.py` 3 passed.

## 2026-08-15 - A3 cash-EOD WATCH discovery

- File A Â§25.25.4 profiles `DISC_EOD_MOMENTUM/RECOVERY/RANGE/LIQUIDITY/NARROW_SESSION`
  as `discovery_reason` only. Not `FTR-018`. Not EvidenceClaim. Not rank.
- Prior close = session direction. PIT percentile = importance. Both required.
- Stale cash and banned symbols cannot WATCH. `can_rank=false`.
- Routes: `POST /api/v1/selection/cash-discovery/refresh`,
  `GET /api/v1/selection/cash-discovery/latest`.
- Tests: `test_cash_a3_discovery.py` 3 passed.

## 2026-08-15 - A2 cash identity and S0/S1 safety

- Resolve A1 staging rows to `InstrumentIdentity` + `NormalizedFact`.
- S0 source health and S1 identity/calendar/ban gates. Ban veto only when
  artifact, date, schema and freshness are proven. Missing/stale ban is
  `WAIT_RESTRICTION`, not REJECT or pass. MWPL stays missing and does not
  block cash. `can_rank=false`. No CONFIRMED. No invented direction.
- Routes: `POST /api/v1/selection/cash-identity/refresh`,
  `GET /api/v1/selection/cash-identity/latest`.
- Tests: `test_cash_a2_identity.py` 5 passed.

## 2026-08-15 - A1 cash last-good staging

- Parse and persist cash last-good as typed `SourceResult` plus
  `cash_staging_rows` (migration `0008_cash_a1_staging`).
- No `NormalizedFact`, no direction claim, no rank, no F&O, no Live Ops
  decision card. Ceiling stays WAIT. `can_support_confirmed=false`.
- Routes: `POST /api/v1/selection/cash-staging/refresh`,
  `GET /api/v1/selection/cash-staging/latest`.
- Tests: `test_cash_a1_staging.py` 3 passed.

## 2026-08-15 - R1 persisted selection runs

- Added File A STO-006/007/008 tables: `selection_scan_runs`,
  `selection_candidates`, `selection_state_events`.
- `POST /api/v1/selection/live/refresh` builds a WAIT batch, diffs it against
  the previous stored run, and persists it. `GET /api/v1/selection/live`
  returns the latest stored run when one exists.
- No CONFIRMED rows are stored. Quantity is still absent. Activation stays
  false. This is durable run/candidate/event JSON, not a full voting claim
  stream.
- Live Ops: Persist research run button.

## 2026-08-15 - R0-B field-by-field proofs and named waivers

- Reviewed the six R0-B official sources against parsers and File A AMEND-A-001.
  Genuine fields (timezone, session, calendar, schema id, identity, watermark,
  fallback) are compiled. Shared HTTP retry/rate/breaker/retention stay
  **named waivers**, not compiled field values.
- MWPL keeps a named waiver: no verified official percentage artifact. Ban
  file still cannot satisfy MWPL.
- Cohort report: `reviewedCount=6`, `provenCount=0`, all `canVote=false`,
  `sourceActivationReady=false`, `gateAuthorized=0`. H1A0 remains 6/6.
- At this step R1 persistence and R2 activation were not yet started.
  **Later the same day:** R1 STO tables + live/refresh landed (see top entry);
  R2 activation still not started.

## 2026-08-15 - R0-B cohort + honest R1 projection wording

- At this step, `/api/v1/selection/live` was documented as an **on-demand WAIT
  projection** from the latest stored scanner symbols (not yet a persisted
  decision record). Docs and Live Ops copy were corrected for honesty.
- Recorded File A **Â§25.20.1** R0-A / R0-B / R0-C split. R2 is not started.
- Added `GET /api/source-inventory/r0b-cohort` for the first official
  source-contract proof cohort (ban, MWPL, cash EOD, F&O EOD, index/VIX
  context, corporate actions). Extended fields and per-source breakers
  remain WAIT. Every member is quarantined and `canVote=false`.
- `sourceActivationReady` stays false. `gateAuthorized` stays 0. H1A0 must
  remain 6/6.
- **Superseded later the same day** by R1 STO persistence (top entry): GET now
  returns the latest stored run when present.

## 2026-08-15 - R1 live decision DTO started

- Independently re-checked GPT's R0 blockers against current code. The
  workbook pin is already `f1abcdceâ€¦` and H1A0 is 6/6. Discovery/activity
  state no longer uses score. Those two GPT blockers were stale.
- Kept GPT's useful rules: no quantity field on the canonical DTO, no new
  table without migration approval, R5 stays fixture-only, do not freeze
  inventory counts in prose.
- Started File A R1 without source activation or orders:
  `GET /api/v1/selection/live` first returned an on-demand WAIT projection
  (later the same day: STO persist + refresh â€” see top entry).
  Activation-false and missing closed-bar structure force WAIT.
  `executable=false`. Quantity fields are rejected. Raw series stay
  immutable; CA opens a new adjusted series id.
- Live Ops shows that surface (`#liveDecisionPanel`). Fixture rooms
  still use Q5 fixtures. Journal qty=0 remains a journal-only lock.

## 2026-08-15 - H1A0 6/6 re-pin after 3 overlap reviews

- Reviewed the three new unexplained groups and added typed CROSS-001-v2
  dispositions. Did **not** rebuild CROSS-002. Did **not** start R1. Did
  **not** activate sources.
- **NSE bulk.csv:** `nse_bulk_deals_today_csv` and generated
  `source:e8f2bc055c435b8d` are `SAME_DATASET_ALIAS` of the official daily
  bulk tape. Sort/attention only; not FII proof; cannot set state.
- **AMFI portfolio page:** `amfi_monthly_portfolio` and
  `amfi_portfolio_disclosure` are `DISTINCT_SHARED_ENDPOINT`. Directory rows
  are not holdings. Delayed sponsorship only.
- **MCX delivery page:** `mcx_delivery_reports` and `mcx_warehouse_stocks`
  are `DISTINCT_SHARED_ENDPOINT`. Delivery pressure and warehouse inventory
  stay separate jobs.
- Re-pinned `REVIEWED_WORKBOOK_SHA256` to
  `f1abcdce2b451b4ded9d9e9c8eb6bd63fae82853803f60bef60a1651dd52eb0b`.
  Observed: 409 rows, 387 endpoints, 354 contracts, 32 overlap records
  (20 parent/child, 7 alias, 5 distinct). H1A0 **6/6**.
  `sourceActivationReady=false`, `gateAuthorized=0`.
- CROSS-002 129-key living map is unchanged and now reports baseline drift
  (live union 176 / named 157 / runtime 132). That is a separate residual.
- **UI now:** Source Health page and Live Ops both render the ten-rung
  compiler ladder. Inventory drawer remains the frozen workbench.
- Verification: `test_r0_residual_slice.py` plus default compiler workbook
  test passed after the pin. Frontend 157/157 unchanged.

## 2026-08-15 - Auditor upgrade (CROSS-014 / workbook review / TDG / ladder)

- Applied the VERIFIED-WITH-MATERIAL-CAVEATS upgrade order. Did **not** start
  R1. Did **not** rebuild CROSS-002. Did **not** activate sources.
- **CROSS-014 / FUS-008 call-graph:** discovery state is completeness-only
  (`legacy_discovery_state`). Market-activity state is completeness/stale-only
  (`legacy_activity_state`). Changing `detail_score` or `activity_score` cannot
  set `WATCH_LONG` / `WATCH_SHORT`. `SelectionCandidate` still rejects those
  score fields. Scores may sort queues only.
- **Workbook review, no re-pin:** current SHA
  `f1abcdce2b451b4ded9d9e9c8eb6bd63fae82853803f60bef60a1651dd52eb0b` â‰  pin
  `1f76dab1c75252aa8185c97f69fc4e6f74b5710918b9d4b3e4a1566d9c646a43`.
  Identity-only compile: the 29 reviewed URL/contract sets still match
  (`stale_resolution=0`), but **3 new unexplained overlaps** exist:
  NSE bulk.csv (`nse_bulk_deals_today_csv` vs generated key), AMFI portfolio
  disclosure, MCX delivery/warehouse. Re-pinning would hide those 3 groups, so
  the pin stays. Current H1A0 is **5/6**.
- **TDG-GAP-001:** reviewed proofs remain empty. The 15 AMEND-A-001 fields are
  no longer copied from workbook extras or catalog `expected_frequency` /
  `parser_status`. Missing stays missing. `gateAuthorized=0`.
- **CROSS-006:** the read-only compiler ladder is mounted on **Source Health**
  and Live Ops. GREEN is not GATE_AUTHORIZED. Current counts are REGISTERED-only
  (409 rows).
- **R1 blocked** until a later reviewed pin returns strict H1A0 6/6.
- Verification: focused backend tests **17 passed**. Frontend **157/157**.
  Live `GET /api/source-inventory/compiler-report` observed H1A0 5/6,
  `sourceActivationReady=false`, `gateAuthorized=0`. Homepage HTML includes
  both `sourceHealthLadder` and `maturityLadder`. Existing compiler tests that
  pin the old workbook SHA still fail for that pre-existing drift and were
  not rewritten to fake 6/6.

## 2026-08-15 - R0 residual slice (superseded by auditor upgrade above)

- First residual pass. Later the same day, inferred TDG proofs were emptied,
  `detail_score` was removed from discovery state, and the workbook was
  reviewed without a re-pin. Treat the newer 2026-08-15 section as current.

## 2026-08-14 - Bundled Inventory Workbench on :8000

- Copied an allow-listed, hash-pinned runtime snapshot from the unchanged
  `D:\trendforge_inventory_app` into `frontend/inventory-workbench/`. The
  snapshot contains 24 required HTML/CSS/JS/catalog/reference files; caches,
  backups, temporary output, pytest debris and `node_modules` were excluded.
- `frontend/inventory-workbench/inventory-workbench.manifest.json` records
  source and copied SHA-256 values. All 24 copied hashes are identical. The
  34.8 MB catalog hash is
  `AD302402FC2D251A995C1A065C02269F1C924A53A7800510B28FCA5033C652CB`.
- The command-room drawer now loads same-origin `/inventory-workbench/`; the
  old `127.0.0.1:8080` dependency is removed. It is a host-owned iframe shell:
  desktop opens at `top:2vh`, `width:95vw`, `height:96vh` (leaving 5% of the
  terminal visible); at `<=760px` it becomes `100vw` by `100dvh`.
- `frontend/index.html` cache-busts `theme-final.css` with
  `20260814-inventory3`. `frontend/tests/inventory-workbench.test.js` verifies
  the 24-file manifest, required script order, same-origin route and the final
  desktop/mobile CSS overrides.
- Runtime observation: the embedded page rendered 165 catalog cards, 129 unique
  keys and the existing live-panel overlays. `GET /api/panels/live` returned
  `trendforge.livePanels.v1`; the FII endpoint returned 349 large deals and
  462 holding/reference rows.
- Verification: copied JavaScript syntax passed; frontend contracts passed
  `154/154`; the focused snapshot test verified 24/24 files; focused
  live-panel, FII and refresh backend tests passed `21/21`. After the expanded
  drawer update, the focused snapshot and Q5 contract tests passed again, and
  Playwright at 1538x698 observed a loaded iframe at 1461x670px
  (95.0% x 96.1%); 390x844 mobile full-screen rendering was also observed.
  The full backend baseline remains
  `803 passed / 20 failed` in unrelated pre-existing source, IV, workbook,
  Upstox and resolver tests.
- This is a read-only research-glass integration. It adds no downloader, scorer,
  state authority, source activation, CONFIRMED path, quantity or execution and
  does not close File A R15, R16 or R18.
## 2026-08-14 - Exact product-fixture chrome on :8000

- User asked for an exact copy of `docs/TRENDFORGE_FINAL_PRODUCT.html` on
  `http://127.0.0.1:8000/` (all rooms, buttons, tables, cards, Structure Lab,
  inventory drawer). The empty WAIT shell was too sparse.
- Live host now loads `frontend/product-fixture.js` (same renderer/data as the
  fixture file). All 14 tools, All Stocks table/cards, radar, stock tabs,
  options lab, paper pipeline and source cards render as in the file preview.
  Numbers remain labelled fixture / not live market evidence.
- Wired APIs stay under **Live Ops** in the left nav. Journal qty remains 0.
  Tests: 153/153. Hard-refresh the browser (Ctrl+F5).

## 2026-08-14 - Runtime frontend shell alignment (not R15)

- Implemented `docs/fable/FRONTEND_SHELL_ALIGNMENT_PLAN.md` as a **seam**:
  `http://127.0.0.1:8000/` now uses FINAL_PRODUCT chrome (All Stocks default,
  14 tool rooms, Structure Lab, Radar, Stock, Options, Paper, Sources, File A
  S0â€“S9 flow) while **keeping** `app.js` + `q5-contract.js` as the only
  renderer. Fixture `stocks` / `decisionTools` / `allStockRows` were **not**
  copied.
- Live remounts: `#marketPulse`, Q5 inspector, radar, market-activity,
  MCX commodity context, harmonic scan, source-health, parser, journal,
  alerts, institutional panel. Inventory iframe is **off**.
- Governance in the same change: `journalQuantity` readonly **0** (no
  `min="1"`); public `selectedState` stays WATCH/WAIT/CONFIRMED/REJECT;
  `lockBadge` holds `LOCKED_NO_TRADE`; market-activity chips use
  `canonicalState`; tool rooms render `WAIT_DTO_UNAVAILABLE` with **no**
  `m_factor` fallback. Flow poster uses File A S4=structure, S5=enrichment.
- New file: `frontend/theme-final.css` (`@scope (.final-shell)`). Acceptance:
  `151/151` (`node tests/q5-contract.test.js && node tests/acceptance-check.js`).
  JS syntax checks passed. SHA-256 prefixes: index `189CD1C9F03528E2`,
  app.js `6688AF7576113D70`, theme-final `2A5BD50FE28B42E5`.
- This does **not** close File A R15, R16 or R18. No
  `GET /api/v1/research/board`. No second downloader.

## 2026-08-14 - Static product preview: complete research-terminal surface

- Extended `docs/TRENDFORGE_FINAL_PRODUCT.html` only; runtime frontend and
  backend decision authority were not changed.
- Added `All Stocks` as the default Discovery surface with eight clearly
  labelled fixture rows, table/card layouts, search, mode, direction, state and
  sort controls, plus research entry, invalidation, T1/T2 and R:R semantics.
- Added the compact operations header with research-only mode, history date,
  timeframe and refresh controls; fixture/live-update metrics; a newer-snapshot
  notice; and the non-authoritative Lightning activity strip.
- Added side-by-side stock decision cards with green/red evidence-direction
  rails, public state, research geometry, confidence components, gate checks,
  selection rationale and an explicit signal timestamp. These are comparison
  surfaces over fixture DTOs, not buy/sell commands.
- Added `Structure Lab` under Swing Research with combined Elliott primary and
  alternate counts, harmonic XABCD/PRZ geometry and an explicit one-STRUCTURE-
  family cap. Stock Evidence now includes Chart & Structure, History & Replay,
  Options/Gamma, Source Lineage, PKScreener and a locked Model Lab.
- Added the read-only Inventory Workbench drawer targeting
  `http://127.0.0.1:8080/`. It is an optional embedded/local reference surface;
  it does not merge inventory-app state, fetchers, scoring or authority into
  TrendForge.
- Missing levels remain `PENDING`, `UNKNOWN` or `REJECTED`; green/red rails are
  evidence direction only. No order, quantity, probability or new CONFIRMED
  authority was added.
- Verification: JavaScript syntax and required feature anchors passed; HTML
  parsing found 55 unique IDs, 56 buttons and 9 required sections with no
  duplicate IDs. The user observed the desktop file preview loading correctly.
  Automated desktop/mobile Playwright regression remains pending because the
  automation browser could not consume the local file/temporary server.
- This closes only the static product-vision fixture slice. Runtime R15 Scanner
  Lab DTO wiring remains open; R16 production PIT/replay and R18 model
  governance remain open. Fixture data cannot authorize a production state.

## 2026-08-13 - Four populated third-party FII cards

- Registry remains one 123-source collector plane. Existing `run-source`
  acquisition persisted `SUCCESS_NEW` last-good objects for Screener.in 105,
  Tickertape 300, Dhan 32 and Equitymaster 25 rows, all dated 2026-08-13.
- Inventory is **165 cards / 129 logical keys / 122 painted primaries**. Cards
  162-165 contain samples and are honestly labelled `THIRD_PARTY`, zero-score
  and non-voting.
- FII API observation: 349 large deals, 462 holding/reference rows and 351
  resolved symbols. Identity uses ticker/ISIN or exact unique official-universe
  name mapping; unresolved names remain visible as `NAME ONLY`.
- Equitymaster now preserves current, previous and changed FII percentage;
  Dhan's missing holding level remains null rather than 0.
- Verification: 14 focused backend tests passed; Python source compilation,
  FII panel Node test and 165-row catalog test passed; browser rendering was
  observed. Consensus and Screener formulas were unchanged.
- Open: TrendForge command room (`frontend/index.html`, `frontend/app.js`)
  still does not call `/api/institutional/fii-stock-signals`. Next slice
  `TF-APP-FII-M1`.

## 2026-08-11 - Official BSE/RBI contracts and calculated research outputs

- Added three production contracts through the existing collector/store plane:
  `bse_financial_results_xbrl`, `bse_shareholding_pattern`, and
  `rbi_tbill_yield`. The registry is **119/119**, schedules remain
  `PROVISIONAL`, and `activation_ready=false` is unchanged.
- Observed saved last-good objects: BSE financial filing index **5,126** rows
  dated 2026-08-10; BSE shareholding filing index **5,508** rows dated
  2026-08-10; RBI 91/182/364-day T-bill auction yields **3** rows dated
  2026-08-05.
- Added internal `CALCULATED_INFORMATIONAL` materialization without adding
  source links: exact-industry peers **500**, prospective PCR/Max Pain **1**,
  and Black-Scholes-Merton Greeks **65**. Every row is `scoreEligible=false`,
  `voteEligible=false`, and `canUnlockReady=false`.
- `fundamental_ratios_v1` is implemented and tested but correctly persists no
  rows yet: the BSE contract is a filing-discovery index, not context-aware
  numeric iXBRL facts. Missing PE/PB/ROE/ROA/debt values are not zero-filled.
- Inventory projection is **161 cards / 125 logical keys** with all **119**
  registry keys represented. `consensus.js` and Screener score formulas were
  not changed.
- Verification: 66 focused source/registry/scheduler tests passed; the final
  matrix/source/calculation acceptance slice passed 52/52; targeted Ruff and
  Python compilation passed; all 13 Inventory Node suites passed. A broader backend run exposed unrelated
  existing failures, recorded honestly in `docs/VALIDATION.md`.

## 2026-08-11 - Pack 7 source reconciliation

- Pack 7 is closed as VERIFIED WITH CAVEATS.
- All 2,019 input lines were reviewed and all 17 meaningful candidates have one
  terminal classification in
  `docs/fable/evidence/pack7-20260811/PACK7_SOURCE_RECONCILIATION.json`.
- No new production key was justified: 4 existing output groups are reused,
  10 login/credential/manual-contract routes are blocked, and 3 synthetic,
  scraping or duplicate-pipeline proposals are rejected.
- NSE option chains and Max Pain reuse the populated production objects already
  live-rerun for Pack 6. Synthetic Greeks and prediction scores remain absent.
- Registry remains 112 sources and catalog remains 154 rows / 118 logical keys.
- Acceptance: 58 focused tests passed and targeted Ruff passed.

## 2026-08-11 - Pack 6 source reconciliation

- Pack 6 is closed as VERIFIED WITH CAVEATS.
- The production registry remains 112 sources; no duplicate downloader or
  speculative key was added.
- Existing NSE option-chain acquisition was live-rerun and persisted for the
  2026-08-10 trading date: attempts 1531-1534 with 18, 6, 113 and 84 rows.
- `parse_nse_option_chain` v1.1.0 recovers canonical symbol/expiry from the
  request URL when a CE/PE contract omits them and fails closed otherwise.
- Acceptance: 54 focused tests and targeted Ruff passed.
- Automated Screener/Trendlyne scraping, credentialed Dhan option data,
  synthetic Greeks and the supplied mock ingestion plane were not activated.

## 2026-08-11 - Pack 5 public smart-money sources closed

Pack 5 is verified with caveats. `nse_market_status` and
`rupeevest_mf_flows` were added through the existing resolver/parser/archive/
MarketDataStore path. The existing `nse_pit_symbol` contract was repaired from
an always-empty market-wide request to bounded per-symbol fan-out; parser
v1.1.0 now preserves the disclosed BUY/SELL direction without scoring it.

Live acceptance: market status 6 source / 5 normalized rows (snapshot 498,
attempt 1525); RupeeVest 1,148 / 1,148 rows (snapshot 497, attempt 1524); PIT
100 / 100 rows across five symbols (attempt 1526). Registry is 112/112/112,
catalog is 154 rows / 118 logical keys, and schedule activation remains false.
The exact candidate ledger is in `docs/fable/ADD_40_SCREENER_LINKS_PLAN.md`.
## 2026-08-06 - Dynamic refresh and scheduler panel handoff repaired

Manual Refresh and scheduled checkpoints now converge on the same latest
hash-verified usable manifest. The reader skips newer `MISSED`/empty audit
manifests instead of letting them mask the previous populated snapshot. A
completed Refresh forces a canonical reread, bypassing the five-minute panel
cache. All successful normalized registry sources enter the supporting overlay
automatically; critical LIVE inputs, Consensus voters and Screener score terms
remain explicit and unchanged.

Observed Refresh-button run: **69 attempted, 67 populated, 2 valid-empty,
0 failed**, committed as
`data/market_data/2026-08-06/snapshots/manual-20260806-144047/manifest.json`.
The current foreground scheduler process is running and recorded late earlier
slots as `MISSED`; those audit manifests no longer empty the panels. Browser
observation: Sector 38/38, Consensus 8 boards / 60 symbols, Nifty Filter 3 BUY
/ 3 SELL, Screener 200 rows / 2,867 extracted symbols. Focused backend:
55 passed; four frontend suites passed; changed-file Ruff and compile checks
passed. The foreground process is not a Windows logon task and is not claimed
restart-persistent.

## 2026-08-06 - Saved MD69 data restored to all research panels

Fixed the live-panel entry gate so `TRENDFORGE_LIVE_PANELS_ENABLED=false`
continues to block the legacy network fetcher but no longer hides a committed,
hash-verified MD69 manifest. Browser observation showed 38 Sector rows,
Consensus stock names (8 boards / 61 symbols), Nifty Filter BUY/SELL names and
200 Screener rows. Focused backend tests: 52 passed; all four frontend suites,
Ruff and compileall passed. See
`docs/fable/MD69_SAVED_PANEL_OVERLAY_REPAIR_2026-08-06.md`.

## 2026-08-06 - Verified corrected full refresh

Restarted the API with the repaired MD69 code and collector flags, then ran the
full registry refresh. Final manifest: **69 attempted, 67 populated, 2 valid-
empty, 0 failed**. The two valid-empty sources were `nse_daily_buyback` and
`nse_pit_symbol`; no source failure remained. Manifest:
`data/market_data/2026-08-06/snapshots/manual-20260806-140044/manifest.json`.

## 2026-08-06 - MD69 seven remaining source repairs

Repaired the remaining SLB, CFTC Legacy/TFF/bundle, NSE Large Deals, AMFI and
NSDL collection failures through the existing MD69 acquisition and parser
spine. No downloader, database, score formula, consensus voter or broker path
was added.

Observed final seven-contract canary: **7/7 `SUCCESS_NEW` and
`PARSED_STRUCTURED`**. Source rows were SLB 277, CFTC Legacy 12, CFTC TFF 9,
CFTC bundle 32, NSE Large Deals 357, AMFI 440 and NSDL 48. Focused/broader
regression: **66 passed**; Ruff and Python compilation pass. Details:
`docs/fable/MD69_REMAINING_SOURCE_REPAIRS_2026-08-06.md`.

## 2026-08-05 - MD69 operation reference synchronized

The verified source/collector/panel maintenance map is now
`docs/fable/MD69_REFRESH_OPERATION_REFERENCE.md`. It records exact code
ownership, manual/scheduled flow, last-good behavior, panel membership, source
add/remove steps and tests. It also corrects two overbroad statements: the
button remains labelled `Refresh` while status text reports download progress,
and a panel can remain unavailable when no eligible saved source exists.

## 2026-08-05 - Registry-Driven Manual Refresh and Last-Saved Panels

The existing MD69 collector now supports one lease-protected `run-all` path and
localhost start/status endpoints. The inventory SPA displays an exact `Refresh`
button plus the six registry scheduler checkpoints. Source selection and counts
come from the loaded registry, so new validated registry rows join without a
frontend source list change.

Failed or empty attempts cannot replace last-good objects. New manifests project
that saved object, original data date, fetch timestamp and hash as
`STALE_LAST_GOOD`. Sector, Consensus and Screener accept the saved projection
for research in open or closed sessions, but only <=300-second required sources
can display green `LIVE`; closed is red `MARKET CLOSED`.

Later observed manual run: 69 sources; 09:00/09:17/10:30/12:30/13:30/15:00
IST; 54 successes, 2 valid-empty results and 13 failed attempts; ten same-day
panel overlays; bhavcopy 2,416 source / 2,122 normalized rows. Focused backend
38 passed, frontend 11/11 passed. The installed automatic task was observed
enabled and running.

## 2026-08-05 - Closed-Session Current-Data Bridge Repair

The live-panel API now consults the hash-verified canonical MD69 manifest after
market close and exposes same-day saved EOD/research sources as
`RESEARCH_ONLY`. It no longer returns an empty overlay merely because the
session is closed. The frontend independently clears cached calculation rows
before applying this overlay, preventing an older intraday source from
overriding current bhavcopy data.

Observed current sources: NSE bhavcopy 2,416 rows, large deals 152, T2T 431,
and PR snapshot 2,476 before response-size projection. Missing current sources
remain missing; specifically, `nse_all_indices` was not collected today, so the
sector panel cannot be called current. No consensus or screener scoring formula
was changed.

Focused backend tests: 18 passed. Frontend: 10/10 scripts passed. Browser proof
matched BAJFINANCE `1158.80 / +0.85%` to the 2026-08-05 normalized bhavcopy.

## 2026-08-05 - MD69-M7 Automatic Collection Activated

Automatic 69-source collection is active under the user's explicit provisional
schedule override.

- SQLite-consistent 257,232,896-byte backup created and integrity verified.
- Additive MD69 migrations `0020` and `0021` applied; production DB integrity
  remains `ok`.
- Windows task `TrendForge MD69 Collector` is running at user logon with
  `IgnoreNew` duplicate protection and restart-on-failure settings.
- First real acquisition populated eight normalized last-good sources.
- Live observation found and fixed excessive EOD retries; incomplete sources
  now wait 15 minutes. No busy-loop writes were observed over 20 seconds.
- Final focused M1-M7 suite: 90 passed, 1 warning.

Schedule evidence remains provisional and source failures remain visible.
No broker, quantity or order behavior was added.

## 2026-08-05 - MD69-M6 Verification and No-Network Dry Run

M1-M6 are implemented and verified at the fixture/temporary-data ceiling.

- Added an explicit deterministic runner over the real MD69 registry, service,
  store and scheduler with a transport that cannot call market URLs.
- The sample 09:17 run completed 25/25 due sources and wrote one 69-entry
  manifest plus a 69-row health projection.
- Registry authority remains `PROVISIONAL`, all 69 sources remain
  `activation_ready=false`, and production activation remains off.
- Evidence is under `docs/fable/evidence/md69-m6-20260805/`.

Observed verification: 89 focused MD69 tests pass; all ten frontend Node suites
pass; Ruff and Python compilation pass. The full backend is not clean: 622
passed and eight inherited non-MD69 failures remain. No production migration,
network collection or background scheduler occurred.

## 2026-08-05 - MD69-M5 Timestamp Alignment and Canonical Panel Bridge

Added a fail-closed derived-input alignment contract and a read-only bridge
from the canonical MD69 manifest into the existing live-panel service.

- Every derived input carries source key, content hash, data/fetch timestamps,
  trading date, normalized records and computed maximum skew.
- Missing, wrong-day, future or over-skew bundles return `WAIT`.
- The panel provider verifies the SQLite manifest hash, manifest file, contained
  object paths and object content hashes before cloning records.
- Canonical mode never creates the legacy live downloader and never falls back
  to static catalog prices when canonical data fails.
- The catalog inventory, Consensus formula and screener A-only formula remain
  unchanged. Production activation remains off.

Observed verification: 17 alignment/live-panel tests; 87 combined M1-M5
backend tests; all 10 frontend Node suites; Ruff and Python compilation pass.

## 2026-08-05 - MD69-M4 Scheduler, Lease, Health, and CLI

Added the foreground-only MD69 scheduler and command contract.

- Exact IST checkpoints: 09:00, 09:17, 10:30, 12:30, 13:30, 15:00.
- Due-only service calls with complete 69-source manifests.
- Holiday filtering keeps NSE-session sources closed while allowing only
  publisher rules that explicitly permit closed-day checks.
- Late/restart slots are recorded once as `MISSED` without overwriting a good
  slot manifest.
- Per-source EOD polling starts at 15:35 and stops only on current-date success.
- SQLite singleton lease, expiry recovery, source health and bulk state reads.
- CLI names are installed, but real execution remains disabled and provisional
  schedules cannot activate.

Observed verification: 14 focused scheduler tests; 80 combined MD69/source/
calendar/live-panel tests; Ruff and compilation pass. No production migration,
background process or market fetch occurred.

## 2026-08-05 - MD69-M3 Unified Acquisition and Normalization

Added one bounded async service over the existing endpoint client and source
resolver. It emits one normalized contract per source and optionally writes
validated output through the MD69 store.

- All 69 profiles have a supported structured or named adapter.
- Parameter providers/fan-out fail closed when required inventory inputs are
  absent.
- Global and per-domain concurrency caps, a queued-call-aware circuit breaker,
  response reuse, and session-only sharing are distinct and tested.
- Verified empty responses follow each source contract. Parser/schema/future-
  date failures and partial batches cannot replace last-good data.
- One source failure cannot cancel unrelated work.

Observed verification: 19 service tests passed; 82 combined source/storage/
adapter tests passed; Ruff and compilation passed. All transports were injected
offline fixtures. No scheduler or production activation was added.

## 2026-08-05 - MD69-M2 Content Store, Manifests, and Safe Retention

Implemented the approved local MD69-M2 storage boundary without touching the
production database.

- Added SHA-256 content-addressed objects with atomic installation and
  cross-day byte deduplication.
- Added an additive `0020_market_data_69_store` schema exercised only against
  caller-supplied temporary SQLite databases.
- Added source attempt history and last-good pointers; failed attempts cannot
  replace valid data.
- Added deterministic atomic manifests with unique source entries and object
  reference lineage.
- Added dry-run-first retention for five completed trading days, current-day
  protection, root containment, nested symlink/reparse refusal, and
  reference-aware object collection.

Observed verification:

```text
focused storage tests: 13 passed
storage + registry + source/calendar/live-panel tests: 47 passed, 1 warning
Python compileall: PASS
Ruff changed files: PASS
```

No network call, production migration, scheduler, panel, consensus, screener,
broker, quantity, or order behavior changed.

## 2026-08-05 - MD69-M1 69-Source Registry Contract Freeze

Implemented the approved MD69-M1 contract-only milestone. No live market fetch,
production database migration, scheduler activation, panel overlay, consensus
change, screener formula change, broker path, quantity, or order path was added.

- Copied the exact 69-row registry into `config` and pinned its approved
  SHA-256 `416C670181E2F2BAB685C9314E3B8D1CC7A4B707413E3E680F8E153B91814FEC`.
- Added YAML-backed typed profiles for all 69 sources: endpoint/resolver owner,
  normalized key, required parameters, provider/fan-out, parser/adapter,
  validator, and response-reuse/session-sharing mode.
- Added a fail-closed offline compiler. It rejects hash/key drift, duplicate or
  missing rows/profiles, unknown components, uncovered parameters, inconsistent
  groups, and provisional activation.
- All schedules remain `PROVISIONAL`; `activation_ready=false`; stale thresholds
  remain unset rather than being represented as official evidence.
- Compiled coverage: 69/69 components verified; 48 existing async-endpoint
  profiles and 21 existing resolver/monitor profiles; 52 independent, 4
  response-reuse, and 13 session-sharing contracts.

Observed verification:

```text
focused registry + runtime/calendar/live-panel tests: 34 passed, 1 warning
registry tests alone: 13 passed
Python compileall: PASS
Ruff changed files: PASS
frontend: 135/135 checks passed
full backend: 551 passed, 24 pre-existing failures, 2 warnings
```

The 24 full-suite failures reproduce the known baseline categories (sandbox
DB/report/parquet writes, missing async pytest plugin, older NSE seed/config
expectations, and existing workbook/source-map drift). No MD69-M1 test failed.

## 2026-08-04 - Seven Inventory Gap Feeds Integrated

Implemented the approved research-only source extension through the existing
monitor, resolver, raw archive and structured-parser spine. No second downloader,
broker route or activation authority was added.

- Added T2T, Kite derivative lot schedules, NSE board meetings, most-active
  futures, most-active options, IPO calendar and PR market snapshot contracts.
- Reused one PR ZIP fetch per multi-source run for bhavcopy, T2T and PR parsing.
- Empty/rate-limited checks retain the latest populated archive for these feeds.
- Refreshed `nse_bhavcopy_eod` with PR ZIP fallback.
- Exported compact normalized browser evidence; the 110,964-row Kite dump became
  247 underlying schedules and remains `OPEN_SOURCE_UNOFFICIAL`.
- Updated `LINKED_SOURCES` from 105 to 112 rows and kept
  `sourceActivationReady=false`.

Observed live normalized counts: bhavcopy 2,415; T2T 447; lot schedules 247;
board meetings 20; futures 36; options 133; IPO 4; PR market rows 2,434.

## 2026-07-29 - Grok Residual Governance Closure

Closed the three residual single-spine gaps identified by the independent Grok
recheck without changing runtime behavior:

- competing-order validation now rejects `Pick next milestone M10`, `Next
  milestone M10`, `Choose the next M10` and `Do next M10`; an immediately
  negated prohibition remains safe, while mixed safe plus unsafe content fails;
- work selection now uses one File A requirement ID: `R0-R18`, `CROSS-###`, or
  `TDG-GAP-###`; `M/T/PK` remain subordinate detail tags and cannot select work;
- `Q4W-006` now matches canonical `FMR-011`: R15 presentation shell, R16
  deterministic replay/path labels/PIT dataset, and R18 challenger
  evaluation/promotion/rollback.

Observed verification:

```text
python -m pytest docs\fable\remaining_build\test_build_coverage_csv.py -q
25 passed in 0.31s

python docs\fable\remaining_build\build_coverage_csv.py --check --decision-inventory [containment arguments]
count=29 max=D-029 next_free=D-030 duplicates=[]
Rows: 155; added=[]; removed=[]; changed=[]
P0 build rows=41; P0 not implemented=48

$env:PYTHONPATH='D:\TrendForge\backend'; python -m pytest -q backend\tests
534 passed in 101.42s

cd frontend; cmd /c npm test
135/135 checks passed
```

Protected runtime hash before edits was
`643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D`.
This closes governance wording and validation only; it does not implement an FMR
runtime feature, activate a source, authorize `CONFIRMED`, or add execution.
## 2026-07-29 - Single Build Spine Residual Closure (governance only)

This entry supersedes the incomplete `8 passed` and manual 240-file containment
proof in the earlier same-day entry while preserving that evidence as history.
Decision `D-029` remains the only Single Build Spine owner; no `D-030` or new
roadmap was created.

Completed residual corrections:

- File A and Final Merge now define the exact `FMR-011` owner split: `R15`
  presentation shell, `R16` deterministic replay/path labels/PIT dataset, and
  `R18` challenger evaluation, promotion, drift demotion and rollback.
- Discovery is now a pure detail catalog. Its machine table has exactly 33 rows
  with `Detail tag | File_A_owners | FMR_refs | Notes`; every owner is covered
  by the union of the referenced canonical File A FMR owners.
- The global M-arrow graph, numbered S1-S10 sprint table, `Start with Phase T0`
  instruction and residual T0/S2 ordering language were removed while retaining
  all capability, prerequisite and acceptance content as per-tag/catalog detail.
- Options and Discovery activation ceilings are conditional on the current
  observed runtime state; neither document hardcodes false activation as a
  permanent product law.
- The remaining-build README now contains the complete R-first work-packet
  template and the exact runtime-source manifest scope.
- `build_coverage_csv.py` now validates detail R/FMR references, exact 33-row
  coverage, owner inclusion, duplicate decisions, permanent activation claims,
  schedule traps, changed-file scope and runtime-source hash equality. Supplying
  `--changed-file` without `--expected-runtime-manifest-hash` fails closed.
- `PLAN_REQUIREMENT_COVERAGE.csv` remains synchronized at 155 rows with zero
  added, removed or changed rows.

Observed verification:

```text
python -m pytest -q docs\fable\remaining_build\test_build_coverage_csv.py
19 passed in 0.33s

python docs\fable\remaining_build\build_coverage_csv.py --decision-inventory
count=29 max=D-029 next_free=D-030 duplicates=[]

python docs\fable\remaining_build\build_coverage_csv.py --check \
  --expected-runtime-manifest-hash 643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D \
  [repeatable approved --changed-file paths]
Rows: 155; added=[]; removed=[]; changed=[]
P0 build rows=41; P0 not implemented=48

$env:PYTHONPATH='D:\TrendForge\backend'; python -m pytest -q backend\tests
534 passed in 99.69s

cd frontend; cmd /c npm test
135/135 checks passed
```

The automated protected runtime manifest covers 119 source files: all
`backend/trendforge_api/**/*.py` plus `frontend/app.js`, `index.html`,
`q5-contract.js` and `styles.css`. Before and after SHA-256 is identical:
`643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D`.

This closes the residual **governance** hardening only. It does not implement an
FMR runtime feature, activate a source, authorize `CONFIRMED`, add quantity or
execution, or make the whole application production-ready.
## 2026-07-29 - Single Build Spine Structural Enforcement (governance tooling)

This corrective record supersedes the governance claims in the earlier
2026-07-29 dual-spine entry while preserving that entry as history. The correct
decision owner is **D-029 Single Build Spine**; **D-025** remains Canonical
Inventory Compiler and Source-Activation Ceiling.

Implemented:

- File A section 25.21 remains the canonical `FMR-001..011` owner map.
- Final Merge and remaining-build README owner/link maps are structurally
  required to equal File A; coverage FMR owner rows must equal the same map.
- `FMR-010` means every applicable `R0-R18` owner, not one all-at-once build.
- Discovery `M0-M23`, `T0-T4` and `PK-A..PK-D` are fully R-owned detail tags;
  `M17` is owned by `R0`. Top-to-bottom M order, T phases, PK phases and
  independent next-step instructions were removed without deleting capability
  requirements.
- Options is an `R12` detail catalog. `M10/M11` are navigation tags and cannot
  select implementation work.
- `build_coverage_csv.py` now parses Markdown tables, validates owner/link-map
  equality, detects missing/duplicate/invalid detail owners, rejects duplicate
  decision IDs, traps competing build instructions and enforces a repeatable
  changed-file allowlist.
- The README allowlist and executable allowlist must match exactly.
- `PLAN_REQUIREMENT_COVERAGE.csv` retained 155 rows; all eleven FMR rows were
  reviewed on 2026-07-29 with no ID addition or removal.

Observed verification:

```text
python -m py_compile docs\fable\remaining_build\build_coverage_csv.py
PASS

python -m pytest -q docs\fable\remaining_build\test_build_coverage_csv.py
8 passed

python docs\fable\remaining_build\build_coverage_csv.py --check [repeatable --changed-file paths]
Rows: 155; added=[]; removed=[]; changed=[]
P0 build rows=41; P0 not implemented=48
PASS

$env:PYTHONPATH='D:\TrendForge\backend'; python -m pytest -q backend\tests
534 passed in 126.57s

cd frontend; cmd /c npm test
135/135 checks passed
```

Backend/frontend runtime manifest before and after was identical across 240
files: `A560FF0834CBD6E89EB624B968485D37EC2D53565EA09EF4EA753F1CCE4367E8`.
This proves scope containment only. It does not activate sources, implement an
FMR runtime feature, authorize `CONFIRMED`, or make TrendForge production-ready.

## 2026-07-29 - Dual-Spine Governance Cleanup (docs only)

Applied Best Final Fix so Discovery/Options cannot act as a second build spine.

- Naming lock: File A = new_merge; File B = Hybrid only; Discovery Detail Plan + Options Detail Plan are detail only.
- Discovery plan: exhaustive M0Ã¢â‚¬â€œM23 / T0Ã¢â‚¬â€œT4 / PK-A..D Ã¢â€ â€™ R*/FMR owner table; forbids Ã¢â‚¬Å“next MÃ¢â‚¬Â as order.
- Options plan: requires File A R12 + FMR-003..008; signed GEX = `SCENARIO_ONLY_NOT_OBSERVED_POSITION`.
- Final Merge: Discovery no longer called File B; requirement vs evidence stacks documented.
- DECISIONS: D-028 updated for FMR-001..011; **D-025** Single Build Spine And Detail-Tag Governance added.
- remaining_build README Ã‚Â§10 FMR-001..011 + Paper Lab vs broker paper; advisory section is Ã‚Â§10A (no dual pure `## 10.`).
- REMAINING_PROJECT_BUILD_FILES: R15/R16/R18 explicitly open FMR-011.
- fileindex: removed `___KEEP___` placeholders; FMR-001..011.
- Product HTML footer attributes File A Ã‚Â§25.21 + FINAL_MERGE + Hybrid File B (fixture only, not runtime FE).
- `build_coverage_csv.py` now runs `validate_governance_docs` (FMR set, dual-spine phrases, KEEP, HTML attribution, D-025/D-028).

```text
python docs\fable\remaining_build\build_coverage_csv.py --check
Rows: 155; added=[]; removed=[]; changed=[]
P0 build rows=41; P0 not implemented=48
```

No runtime backend/activation/OMS/database change.

## 2026-07-28 - Final Merge Addendum Governance Registered

Registered `docs/fable/FINAL_MERGE_PLAN.md` as the mandatory mapped product/design addendum without creating a second build authority or changing runtime behavior.

- `AGENTS.md` now requires the addendum for mapped all-stock, discovery, PKScreener, options, Gamma/GEX, strike/expiry and trader-workflow milestones.
- File A section 25.21 maps `FMR-001..010` aliases into the existing `R0-R18` sequence. File A still owns stable implementation IDs, order, four states, permissions, ceilings and acceptance.
- `remaining_build/README.md`, `REMAINING_PROJECT_BUILD_FILES.md`, `fileindex.md` and `DECISIONS.md` now expose the same role and crosswalk.
- The existing coverage generator and CSV contain ten documented FMR aliases. Coverage is 154 rows: IMPLEMENTED 35, PARTIAL 66, PLANNED 36, POSTPONED 9, CONFLICT 6 and REJECTED 2.
- Coverage verification reports 154 rows with zero added, removed or changed drift after regeneration; 40 active P0 build rows and 47 P0 rows not implemented.

This is documentation and traceability work only. It does not implement an FMR feature, activate a source, grant gate authority, change the current state ceiling, install a dependency, modify storage, or make TrendForge production-ready.
## 2026-07-23 - CROSS-002 Living Source Map And Activation Review Verified

Implemented File A `CROSS-002 / TDG-GAP-013` at the R0 governance ceiling
without editing the source workbook or activating any market-data source.

The former Ã¢â‚¬Å“315 source contractsÃ¢â‚¬Â description was incorrect. The compiler
contains 315 normalized identities: 118 named inventory keys and 197 generated
`source:<hash>` endpoint-lineage identities. The runtime catalog has 74 keys;
63 overlap the inventory, producing one current 129-key living map.

- All 129 living keys have exact origin, mapping disposition, maturity review,
  activation review, blockers, safe use, blocked use and next action.
- All 351 normalized endpoints have exact named-key or
  `UNASSIGNED_ENDPOINT_LINEAGE` disposition; 192 are explicitly unassigned.
- The three reviewed key sets are count- and SHA-256-pinned. Drift makes
  `sourceMapReviewValid=false` and `sourceGovernanceReady=false`.
- `sourceGovernanceReady=true`, reviewed keys are 129/129 and unreviewed keys
  are zero. This means the fail-closed review is complete, not that data is
  live or usable.
- `gateAuthorizedSourceKeyCount=0`, `sourceActivationReady=false` and
  `executionAuthorizedCount=0`. Generated lineage can never authorize a gate.

Verification passed: focused compiler/API **28**, complete backend **533**,
frontend **135/135**, scoped Ruff, observed compiler report, and coverage
regeneration/check. Coverage remains 144 rows with zero drift: IMPLEMENTED 35,
PARTIAL 66, PLANNED 26, POSTPONED 9, CONFLICT 6 and REJECTED 2.

Milestone verdict: **VERIFIED**. `CROSS-002`, `TDG-GAP-013` and
`HYBRID-16-5` are implemented. R0 remains PARTIAL only for separate residuals,
including source-specific extended-field proof, persisted maturity history,
mirror/resolver/authority values, source-health UI migration and raw-versus-
adjusted contracts. Live activation belongs to later source milestones.

## 2026-07-23 - CROSS-001 / H1A0-04 Semantic Overlaps Resolved

Completed the single File A `CROSS-001 / H1A0-04` milestone without editing the
master workbook or starting the next R0 milestone.

- Replaced the free-text overlap bypass with a typed, versioned, exact-key
  registry bound to the reviewed workbook SHA-256.
- Corrected compound prefixed rows so each source key binds only to its own URL;
  this removed three false cross-product overlap groups and two false generated
  source contracts.
- Reviewed all 29 resulting endpoint/contract groups: 20 parent/child, six
  same-dataset aliases and three distinct shared endpoints. There are no
  guessed merges and no active `QUARANTINED_UNPROVEN` entries.
- Wildcards, weak alias evidence, duplicate/conflicting entries, changed
  contract sets and changed workbook hashes fail closed.
- Current observed compiler result: 370 rows, 351 endpoints, 315 contracts,
  complete lineage, zero unexplained/invalid/stale resolutions and H1A0 6/6.
- `sourceActivationReady=false`, all 315 contracts remain unresolved, and
  `executionAuthorizedCount=0`. An identity resolution grants no vote, gate,
  CONFIRMED state, quantity or execution authority.

Verification passed: focused compiler/API **26**, complete backend **531**,
frontend **135/135**, compileall, scoped Ruff lint/format and observed
`GET /api/source-inventory/compiler-report`. The source workbook hash remains
`1f76dab1c75252aa8185c97f69fc4e6f74b5710918b9d4b3e4a1566d9c646a43`.
Coverage remains 144 rows with zero drift: IMPLEMENTED 32, PARTIAL 68,
PLANNED 27, POSTPONED 9, CONFLICT 6 and REJECTED 2.

Milestone verdict: **VERIFIED**. `CROSS-001` is implemented. R0 remains PARTIAL
because its separate source-contract maturity, living-map, activation and
other residual acceptance requirements are not complete. The next milestone
was identified but not started.

## 2026-07-22 - H1A0 5/6 Versus 6/6 Reconciled

Completed the single contradiction-reconciliation milestone for File A
`R0 / CROSS-001 / TDG-GAP-012`. Current compiler and API evidence proves that
H1A0 is **5/6**, not 6/6.

- Checks 1, 2 and 3 pass on the normalized endpoint view while retaining 29
  raw key-prefix defects, 16 raw JSON-key-array defects, two raw compound cells
  and four raw sentinel rows for lineage.
- Check 4 fails because 32 endpoint-to-contract semantic overlaps remain
  unexplained. All 370 rows have lineage, but complete lineage is not semantic
  deduplication.
- Checks 5 and 6 pass: all canonical records retain required use context, and
  F&O ban remains separate from MWPL percentages with no runtime mismatch.
- The workbook was not edited. All 317 contracts remain unresolved,
  `sourceActivationReady=false`, and execution-authorized count is zero.

One adversarial regression now proves that complete lineage cannot hide a
semantic overlap. Verification passed: focused compiler/API **19**, complete
backend **524**, frontend **135/135**, compileall, scoped Ruff and runtime
`GET /api/source-inventory/compiler-report`. Coverage remains 144 rows with
zero drift after the reviewed R0 reason was refreshed.

Milestone verdict: **VERIFIED WITH CAVEATS**. The contradiction is resolved,
but `CROSS-001` and R0 remain PARTIAL until the 32 overlaps receive reviewed
resolutions. Next recommended milestone: `CROSS-001 / H1A0-04` reviewed
semantic-overlap resolution. It was not started in this run.

## 2026-07-22 - R0 H1A0 Defect Contract Verified; CROSS-001 Remains Partial

Implemented File A `R0 / CROSS-001 / TDG-GAP-012` at the compiler-reporting
ceiling without editing the master workbook.

- The compiler/API expose all 11 Hybrid section 16.4 defect classes, including
  zero-count classes, duplicate groups, non-data references, semantic overlaps
  and runtime-contract mismatch.
- Key-prefixed rows without `active_source_keys` retain lineage and merge into
  their source-key contract. Support/reference/local rows are quarantined.
- Every normalized endpoint has role, purpose, safe use, blocked use and next
  action. H1A0 check 4 now tests semantic overlap plus complete lineage instead
  of treating lineage alone as semantic dedupe.
- Current result: 370 rows, 351 endpoints, 317 contracts, 17 exact duplicate
  groups, 32 unexplained overlaps, 370 lineage rows and H1A0 acceptance 5/6.
- All 317 contracts remain unresolved; gate authorization is zero and
  `sourceActivationReady=false`.

Verification: focused compiler/API 18 passed; broader source/API/safety 114
passed; complete backend 523 passed; compileall and touched Ruff lint/format
passed. Coverage is 144 rows with zero drift: IMPLEMENTED 30, PARTIAL 70,
PLANNED 27, POSTPONED 9, CONFLICT 6 and REJECTED 2; active P0 build rows are 42.

Completed-evidence audit: **PASS WITH CAVEATS**. Independence was unavailable
without creating another agent, so the governed audit ran in the main thread
under the reusable TrendForge contract. `TDG-GAP-012` is IMPLEMENTED, but
`CROSS-001` and R0 remain PARTIAL until the 32 overlaps receive reviewed
resolutions. Workbook mutation requires separate approval. Frontend observation
is N/A. No dependency, migration, deletion, deployment, broker access, quantity
or execution behavior was introduced.

This section previously named `CROSS-002 / TDG-GAP-013` as next. The newer
reconciliation above supersedes that unproven ordering; `CROSS-001 / H1A0-04`
remains the first unfinished acceptance item.

## 2026-07-22 - R0 Compiler Gate Authority Repaired; R0 Remains Partial

Adversarial review refuted the earlier assumption that the inventory compiler
controlled runtime confirmation. Fresh structured parser output could still
be promoted to `PASS/CAN_CONFIRM` by the legacy readiness path while the
compiler reported `sourceActivationReady=false` and zero gate-authorized
sources. That bypass is now closed.

- `gate_readiness.py` compiles one workbook-signature-cached activation context
  and requires both global activation and per-contract gate permission before
  any source can reach `PASS`.
- Fresh structured data remains inspectable, but currently reports
  `WAIT_SOURCE_ACTIVATION` and `DO_NOT_PASS_READY`. Optional missing sources no
  longer hide the global activation ceiling.
- Official surveillance and F&O-ban matches remain hard vetoes above the
  activation wait state.
- The legacy unlock helper defaults to false unless callers provide both
  compiler proofs. Every seeded source-replacement row now has
  `can_unlock_ready=0`; descriptive map rows cannot authorize confirmation.
- Coverage was corrected rather than inflated: `CROSS-001` and
  `TDG-GAP-011` are `PARTIAL`; `CROSS-020` belongs to R1; Hybrid aliases now
  agree with their governing rows. The current counts are IMPLEMENTED 29,
  PARTIAL 71, PLANNED 27, POSTPONED 9, CONFLICT 6 and REJECTED 2.

Observed verification: 5 focused adversarial tests passed, the broader source,
API, scheduler and safety set passed 109 tests, the complete backend passed
518 tests, frontend checks passed 135/135, touched Python files passed Ruff
lint/format and compileall, and coverage remained 144 rows with zero drift.

R0 is not complete. Exact H1A0 semantic-overlap/per-row acceptance,
separately persisted maturity transitions, the reviewed 69+43 source-key map,
remaining contract fields, source-health UI migration and other File A R0
residuals remain open. No source is activated and production readiness is not
claimed.

## 2026-07-22 - Superseded Initial R0 Inventory Verification

Historical verification snapshot retained for audit. It initially treated
`CROSS-001` and `TDG-GAP-011` as closed. The adversarial review and repaired
section above supersede those status claims; the test counts and observed
compiler measurements below remain historical evidence.

- The compiler distinguishes `OK`, `INPUT_MISSING`, `INPUT_EMPTY` and
  `SCHEMA_ERROR`; missing or empty inventory can no longer look like a clean
  result.
- It preserves all 370 workbook rows and their raw defects, normalizes 354
  canonical inputs into 351 endpoint identities and 317 source contracts, and
  records four sentinel/status rows separately. This historical snapshot
  incorrectly reported H1A0 as 6/6; current semantic acceptance is 5/6 because
  32 unexplained overlaps remain.
- J01-J14 decision jobs and the complete ten-stage maturity ladder are typed
  and exposed. Status prose such as CONNECTED or FRESH cannot promote a source.
- Every current source contract remains unresolved, gate source count is zero,
  and `sourceActivationReady=false`. Mirror/resolver identities and authority
  caps remain `UNSPECIFIED` instead of being guessed.
- Runtime source coverage is compiled from the workbook contract rather than
  the historical 211-link view. Runtime catalog-only keys are not inserted as
  linked workbook roots.
- The compatibility risk endpoint now returns research geometry only:
  `quantity=0`, `executable=false`, and `POSTPONED_NO_QUANTITY`. A hard safety
  state such as `LOCKED_NO_TRADE` keeps precedence while remaining zero and
  non-executable.
- Institutional evidence direction is independent of quantity. The bounded PK
  fixture worker retains one finite invocation and now uses a ten-second
  default timeout; explicit short-timeout tests still prove timeout handling.

Observed verification: the focused changed-area suite passed 132 tests; the
complete backend suite passed 518 tests; frontend checks passed 135/135;
compileall and full Ruff lint passed; coverage check reported 144 rows with
zero drift. Full Ruff format check still identifies 17 unrelated pre-existing
files, and full mypy reports 324 errors in 42 files, including missing stubs and
existing typing debt. No clean format or mypy claim is made and no dependency
was installed.

Current traceability counts are IMPLEMENTED 30, PARTIAL 68, PLANNED 29,
POSTPONED 9, CONFLICT 6 and REJECTED 2. There are 42 active P0 build rows.
R0 remains PARTIAL: the reviewed 69+43 living-key baseline, remaining
defect-class enforcement not already closed by CROSS-001, source-health UI
migration, real mirror/resolver/authority values and raw-versus-adjusted series
contracts remain open. EvidenceClaim timestamp completion is CROSS-019/R1 in
File A and the coverage CSV; it is not an R0 residual.

## 2026-07-20 - R0 Feature Registry / Indicator Engine Pin Verified

Implemented File A `DAT-010`, `DAT-011`, `T-028`, `T-029`, `T-030`,
`T-194`, and `T-195` at the R0 contract ceiling.

- `feature_registry.py` exposes the exact 39 contracts `FTR-001..FTR-039`
  using the mandatory 22-field schema. Registry lint verifies unique IDs,
  owners, maturity, declared read-only routes and exact feature/engine pins.
- `indicator_engine.py` pins one engine identity per run:
  `trendforge.numpy-pandas` `1.0.0`, observed with NumPy `2.4.3` and pandas
  `2.3.3`. Missing/mixed engines, runtime drift, insufficient warm-up and
  parity divergence fail closed.
- `feature_engineering.py` and `institutional_features.py` require complete,
  unique, chronological inputs and reject partial, mixed or non-finite vectors.
- `selection/contracts.py` binds every `EvidenceClaim` and scan run to the
  registered feature version, evidence family, correlation group and engine
  manifest. Forged IDs/counts and unregistered claims are rejected.
- Read-only `GET /api/v1/selection/feature-registry` and `/lint` expose the
  contract. POST/PUT/DELETE return 405. Only real declared routes can be marked
  `RESEARCH_ACTIVE`; current active entries are FTR-013 and FTR-018.

The first adversarial pass was **REFUTED** because caller-controlled warm-up,
unregistered claims, non-finite outputs, mixed engines and false active routes
could bypass the intended boundary. Those paths were reproduced, fixed and
added as regression tests before the milestone was accepted.

Observed verification: 126 focused tests passed; the complete backend suite
passed with 514 tests; frontend checks passed 135/135; compileall and Ruff
checks for touched files passed; registry/lint runtime observation returned 39
valid contracts; coverage check returned 144 rows with zero drift. A focused
mypy run that followed imports still reports 53 errors in 10 modules, including
missing pandas stubs and pre-existing imported-module typing defects. No clean
mypy claim is made and no dependency was installed.

This is a contract/governance milestone only. It does not activate an
unverified source, authorize production scanning, unlock live `CONFIRMED`, add
execution/quantity behavior, or complete R0.

## 2026-07-20 - R0 F&O-Ban / MWPL Contract Split Verified

Implemented File A CROSS-008 / DAT-015 without adding a guessed endpoint or
relaxing confirmation gates.

- `nse_fno_ban` now owns the official dated `fo_secban.csv` contract and is a
  hard symbol veto; a schema-valid empty file is distinct from fetch/parse
  failure.
- `nse_mwpl_percentages` is a separate source and parser contract. No verified
  official percentage artifact is registered, so absence is explicit
  `WAIT_MWPL_PERCENTAGES`.
- `nse_mwpl_ban` remains only a non-voting compatibility alias and legacy raw
  snapshot fallback.
- G13 requires fresh F&O-ban, MWPL-percentage and FO evidence. Optional missing
  context can no longer mask the specific percentage blocker.
- Primary source-inspector UI exposes the two canonical contracts separately.
- No database schema migration, dependency install, execution route, quantity
  calculation or broker integration was introduced.

Observed verification: 487 backend tests passed; 135/135 frontend checks passed;
Ruff lint and format checks passed; compileall passed. Production readiness is
not claimed because the MWPL-percentage artifact and other R0-R18 work remain
open.
## 2026-07-20 - R0 Inventory Compiler (Hybrid Ã‚Â§16.3Ã¢â‚¬â€œ16.6 / Ã‚Â§18.4 / Ã‚Â§19.2)

Historical snapshot: the current 2026-07-22 section at the top of this file
supersedes this section's compiler acceptance status.

Implemented research-only **source inventory compiler** for File A R0 residuals
and dual-file CROSS/TDG rows. Hybrid sections opened for detail:
Ã‚Â§15.3 (extended contract field list), Ã‚Â§16.3 (maturity ladder), Ã‚Â§16.4 (H1A0
defects/acceptance), Ã‚Â§16.5Ã¢â‚¬â€œ16.6 (utilization/map spirit), Ã‚Â§18.4 (dataset-root
fields), Ã‚Â§19.2 (J01Ã¢â‚¬â€œJ14), Ã‚Â§19.4Ã¢â‚¬â€œ19.5 (ban/MWPL and FX split declarations).

### Code

| Path | Role |
|---|---|
| `backend/trendforge_api/source_inventory_compiler.py` | Defect detection, maturity counts, J01Ã¢â‚¬â€œJ14, dataset roots, contract splits, H1A0 acceptance report |
| `backend/trendforge_api/main.py` | `GET /api/source-inventory/compiler-report`, `GET /api/source-inventory/decision-jobs` |
| `backend/tests/test_source_inventory_compiler.py` | Offline unit + API tests |

### File A ceilings applied

- Public states unchanged (WATCH/WAIT/CONFIRMED/REJECT).
- `researchOnly=true`; `executionAuthorizedCount=0`; roots `canUnlockExecution=false`.
- Linked/CONNECTED does not imply GATE_AUTHORIZED or CONFIRMED.
- Quantity / OMS / execution not introduced.
- Workbook row counts and SHA-256 recomputed at runtime (not frozen prose).

### Honest residual (not claimed complete)

- On 2026-07-20, H1A0 acceptance did not pass. A later historical entry
  incorrectly described the 2026-07-22 normalized view as 6/6. Reproduction
  proves 5/6: check 4 remains open on 32 semantic overlaps. The workbook was
  not rewritten.
- Indicator-engine pin / feature-registry lint are implemented at the R0
  contract ceiling; source/inventory/compiler residuals remain open.
- Named PRF source sets (CROSS-004), activation backlog 1Ã¢â‚¬â€œ20 (CROSS-005), live S0Ã¢â‚¬â€œS3 remain open.
- Ban/MWPL split is **implemented**: `nse_fno_ban` is the canonical official hard-veto contract; `nse_mwpl_percentages` is separate and remains `WAIT_MWPL_PERCENTAGES` until a verified official percentage artifact exists; `nse_mwpl_ban` is a non-voting compatibility alias only.

### Coverage CSV

Updated seed rows for R0 residuals; CROSS-008 is now IMPLEMENTED + TESTED_OFFLINE while CROSS-001/002/003/006/007 remain PARTIAL:
TDG-GAP-001/011/012/013/024/025, HYBRID-2-1. Regenerated via
`build_coverage_csv.py --accept-reviewed-changes`.

## 2026-07-20 - Remaining-Build File Map Role Clarified

`docs/fable/remaining_build/REMAINING_PROJECT_BUILD_FILES.md` is now explicitly
registered across project governance and architecture as the location map for
remaining code, tests and supporting documents. It is read after File A,
current build status and validation when selecting a milestone implementation
surface. It is not a third plan and cannot change File A scope, sequence,
requirement IDs, public states or acceptance ceilings.

Its former ambiguous `Documents (always)` heading was replaced by a priority
contract: P0 is read every milestone, P1/P2 are opened when relevant, and P3 is
preserved audit/history evidence only. References were aligned in `AGENTS.md`,
File A Section 0.5, the remaining-build README, and both architecture maps. This
was a documentation-only clarification; no code, tests, source inventory,
database, dependency or trading behavior changed.
## 2026-07-20 - Remaining-Build Governance and Coverage Repair Verified

The existing `docs/fable/remaining_build/` pack was audited and repaired in
place. No replacement plan, duplicate coverage file, or new authority document
was created. All 137 requirement rows and their best retained ideas remain in
the existing coverage CSV.

Current outcome:

- File A (`docs/fable/new_merge_PLAN_2026-07-18.md`) remains the build-sequence
  and scope authority; File B remains its domain-detail library.
- `remaining_build/README.md`, `REMAINING_PROJECT_BUILD_FILES.md`, `AGENTS.md`,
  and `docs/DECISIONS.md` now use the same authority, scope, and R0-R18 order.
- Quantity calculation, position intent, order intent, broker execution, and
  autonomous trading remain outside the active research-only build. Preserved
  historical/advisory mentions of `READY` or zero quantity are non-operative;
  the current public research states remain WATCH, WAIT, CONFIRMED, and REJECT.
- The CSV generator now validates the complete reviewed 137-ID manifest,
  statuses, priorities, evidence levels, canonical non-future dates, actual
  code/test paths, manifested runtime routes, exact columns, duplicates,
  unknown/manual rows, additions, changes, and removals.
- Normal regeneration refuses added or changed reviewed rows unless
  `--accept-reviewed-changes` is supplied; `--check` is the default audit path.
- Coverage remains 137 rows with 137 unique IDs: IMPLEMENTED 17, PARTIAL 63,
  PLANNED 40, POSTPONED 8, CONFLICT 8, REJECTED 1. All verification dates and
  unresolved-reason fields are populated. P0 has 47 active build rows
  (`PLANNED` or `PARTIAL`) and 56 rows not `IMPLEMENTED` when 8 conflicts and
  1 rejected row are also counted.
- Full verification passed: backend `474 passed`; frontend `135/135`; generator
  compile/check passed with zero drift. In-memory attacks rejected missing
  HYBRID IDs, unmanifested additions, future dates, fake code references, fake
  runtime routes, and unapproved additions. Two final independent Fable attacker
  passes returned `VERIFIED` for generator safeguards and roadmap alignment.

This repair changes governance and audit reliability only. It does not claim
that the remaining Q5/R milestones are implemented or that TrendForge is
production-ready.

## 2026-07-20 - Dual-File Governance Adopted (No Full Hybrid Merge)

File A (`docs/fable/new_merge_PLAN_2026-07-18.md`) remains the only build
authority. File B (Hybrid plan) is a detail library. Gemini dual-file guidance
was adopted with corrections:

- No destructive full-merge of Hybrid into Merge (avoids paste-loss).
- File A gained dual-file preamble + **Ã‚Â§25** CROSS/GAP/POST/CONFLICT index.
- File B gained dual-file preamble + Ã‚Â§20 pointer back to File A.
- Primary sequence stays R0Ã¢â‚¬â€œR18 / Q5-R* (not Hybrid H1Ã¢â‚¬â€œH10 as sprint board).
- Quantity / paper-live execution remain POSTPONE under File A scope.
- Agents must open Hybrid sections listed in File A Ã‚Â§25 while building those rows.

**Recheck (same day):** Gemini points previously thinner or missing were added in
File A **Ã‚Â§25.15** Ã¢â‚¬â€ executive sufficiency/impact wording, permitted/prohibited
actions, best-unique A/B lists, HYBRID-*/MERGE-H* alias map, File-AÃ¢â€ â€™File-B
rationale matrix, H1A*Ã¢â€ â€™R/Q5 dependency map, planned (not live) CI/orphan design,
agent checklist, unresolved evidence needs, Hybrid Ã‚Â§Ã‚Â§1Ã¢â‚¬â€œ19 proof table, and
explicit non-adoptions. Acceptance aliases such as MERGE-H1A0-01, MERGE-H2-01,
MERGE-H1A3-01, MERGE-H5-01 (research rewrite), HYBRID-3-01/6-01/7-01/16-08/17-02
are listed in Ã‚Â§25.13.

**Two-document governance install (same day):** External full analysis saved as
`docs/fable/remaining_build/TWO_DOCUMENT_GOVERNANCE_SYSTEM_2026-07-20.md`. File A gained **Ã‚Â§0.5**
cross-reference authority and **Ã‚Â§25.16** TDG-GAP-001..026 + AMEND-A-001..013
short contracts (pointers, not full-merge). File B gained AMEND-B-002..005 notes
(statesÃ¢â€ â€™reasons, H* superseded, sizing POSTPONE, stale line refs). Hierarchy
corrected: File B is detail library; File A owns sequence and research-only
scope. Code implementation of TDG-GAP contracts remains open.

**GLM re-submit (same content family):** User re-provided the two-document
governance analysis (attributed to GLM). It matches the already-installed package
(GAP-001..026 Ã¢â€ â€™ TDG-GAP-*, AMEND-A/B, external historical 60/35/5 estimate that is not an active measured coverage result, final verdict).
No second full install required. Status remains: **docs installed; code open**.

## 2026-07-20 - Coverage CSV + Kimi/GLM Governance Guide Catalogued

- Read Kimi + GLM dual-file guide (now under remaining_build pack).
- Seeded coverage CSV (~137 rows) from Q5-R0..R7, R0Ã¢â‚¬â€œR18, CROSS, TDG-GAP,
  HYBRID-*, CONFLICT rows.
- **Pack location:** `docs/fable/remaining_build/` with `README.md` for AI next steps.
- Regenerator: `python docs/fable/remaining_build/build_coverage_csv.py`
- Seed status mix (approx): IMPLEMENTED 17, PARTIAL 63, PLANNED 40, POSTPONED 8,
  CONFLICT 8, REJECTED 1.
- File A Ã‚Â§25.17 points at CSV; fileindex catalog updated.
- **Not done:** full paste of every append-ready block into File A body (would
  bloat and duplicate Ã‚Â§25.16). Pointers + CSV + Hybrid remain source of detail.
- **Not done:** code for remaining PLANNED/PARTIAL P0 rows.

No trading action, migration, or dependency install in this docs slice.

## 2026-07-20 - Remaining-Build Pack Folder Created

Moved remaining-build related docs into one folder so they are not confused with
File A/B authority plans or application code:

```text
docs/fable/remaining_build/   (all of the following live only in this folder)
  README.md
  PLAN_REQUIREMENT_COVERAGE.csv
  build_coverage_csv.py
  REMAINING_PROJECT_BUILD_FILES.md
  INDEPENDENT_AUDIT_merge_plan_build_matrix_2026-07-20.md
  INDEPENDENT_AUDIT_hybrid_vs_new_merge_2026-07-20.md
  TWO_DOCUMENT_GOVERNANCE_SYSTEM_2026-07-20.md
  TRENDFORGE_GOVERNANCE_SYSTEM_ai.md
```

**Not moved (still authority / core):** `new_merge_PLAN`, Hybrid plan, BUILD_STATUS,
VALIDATION, fileindex, ARCHITECTURE, code under `backend/` and `frontend/`.

Paths updated in File A Ã‚Â§0.5/Ã‚Â§25, Hybrid preamble, fileindex, VALIDATION.
Docs-only move; no code change.

Proof of gap analysis:
`docs/fable/remaining_build/INDEPENDENT_AUDIT_hybrid_vs_new_merge_2026-07-20.md`.

No application code, dependency, migration or trading change in this docs-only
governance update.

## 2026-07-20 - Merge-Plan Implementation Completeness Audit

Requirement-by-requirement audit of
`docs/fable/new_merge_PLAN_2026-07-18.md` against code, APIs, UI, storage and
tests. Full matrix and disposition detail:
`docs/fable/remaining_build/INDEPENDENT_AUDIT_merge_plan_build_matrix_2026-07-20.md`.
Proof commands and live observations: `docs/VALIDATION.md` (same date).
Remaining-build pack (CSV, audits, AI guides): `docs/fable/remaining_build/README.md`.

### Verdict

| Scope | Status |
|---|---|
| Plan Ã‚Â§24.13 **Q5-R0 through Q5-R7** | **IMPLEMENTED** at approved research/fixture ceilings |
| Plan Ã‚Â§15 **R0 through R18** full vertical | **PARTIAL** Ã¢â‚¬â€ only the Q5 subset is proven |
| Production selection, durable Q5 history, live CONFIRMED | **MISSING** (outside Q5 ceilings) |
| `PST-*` postponed / `REJ-*` rejected items | Correctly **POSTPONED** / **REJECTED** |

The merge-plan document is **not** completely built. Q5-R0 through Q5-R7 are
complete only at their documented ceilings. A class, fixture, endpoint name or HTTP 200
alone is not treated as production implementation.

### Q5-R0 Ã¢â‚¬Â¦ Q5-R7 status (authoritative spine)

| Milestone | Status | Actual modules | API / UI | Storage | Ceiling |
|---|---|---|---|---|---|
| Q5-R0 | IMPLEMENTED (docs) | Plan contract freeze | Docs only | N/A | No production claim |
| Q5-R1 | IMPLEMENTED | `selection/contracts.py`, `fixtures.py` | `GET /api/v1/selection/fixtures/q5-r1` | In-memory fixture | `NO_EARLY_CONFIRMED` |
| Q5-R2 | IMPLEMENTED | `selection/resolver.py`, `r2_fixtures.py` | `GET Ã¢â‚¬Â¦/q5-r2` | In-memory | `WATCH_WAIT_REJECT_ONLY` |
| Q5-R3 | IMPLEMENTED | `selection/structure.py`, `r3_fixtures.py` | `GET Ã¢â‚¬Â¦/q5-r3` | In-memory | `EOD_CLOSED_BAR_RESEARCH_ONLY` (one fixture CONFIRMED) |
| Q5-R4 | IMPLEMENTED | `enrichment.py`, `options_domain.py`, `mcx_contracts.py`, `r4_fixtures.py` | `GET Ã¢â‚¬Â¦/q5-r4` | In-memory | `UNKNOWN_EXPLICIT_NO_MCX_CONFIRMED` |
| Q5-R5 | IMPLEMENTED | `scanners/pk_compatibility.py`, `pk_fixture_worker.py` | No production route; CLI only | Fixture artifacts | Offline harness; zero shadow authority |
| Q5-R6 | IMPLEMENTED | `history_validation.py`, `pit_path.py`, `r6_fixtures.py`; FE `q5-contract.js` | `GET Ã¢â‚¬Â¦/q5-r6` + radar/inspector | In-memory only | `NO_PERFORMANCE_OR_PROBABILITY_UI` |
| Q5-R7 | IMPLEMENTED (boundary) | `openalgo_client.py` + capability route | `GET /api/v1/integrations/openalgo/capability` | Config/env | `NO_INTRADAY_CONFIRMED`; observed state `ABSENT` |

### Five-point acceptance (accepted Q5 work)

For each Q5 milestone above (except pure-doc R0): code exists; it is connected
to runtime (API or intentional CLI); output reaches the correct API/UI; failure
and stale/closed-bar behavior is tested; runtime was observed, not mock-only.
Q5-R5 intentionally has no production HTTP route.

### Full plan R0Ã¢â‚¬â€œR18 vs built

| R-step | Status | Note |
|---|---|---|
| R0 contract freeze | PARTIAL | Feature registry and indicator pin verified at contract ceiling; inventory/compiler/source activation residuals remain |
| R1 radar DTO | IMPLEMENTED (fixture + R6 UI) | Live production scan DTO not authorized |
| R2 live S0Ã¢â‚¬â€œS3 pipeline | PARTIAL | Sources/resolver pieces exist; not one production selection run |
| R3 family resolver | IMPLEMENTED (fixture as Q5-R2) | |
| R4 PK pin + delist fixtures | PARTIAL | Q5-R5 offline pin/harness; full PIT delist set incomplete |
| R5 structure first CONFIRMED | IMPLEMENTED (fixture as Q5-R3) | Not production-authorized |
| R6 enrichment | PARTIAL | Q5-R4 job contracts; live source wiring incomplete |
| R7 PK shadow/CLI | IMPLEMENTED (offline as Q5-R5) | |
| R8 native PK core catalog | MISSING / PARTIAL | Structure native only |
| R9 lifecycle + ORB/VWAP | PARTIAL | History in Q5-R6; ORB/VWAP gated on verified intraday |
| R10 pipe DSL | MISSING | |
| R11 swing RS/delivery + live MCX master | PARTIAL | MCX fixture gates only |
| R12 options timeline API | PARTIAL | Options domain fixture only |
| R13 remaining scanners | IMPLEMENTED / GUIDANCE ONLY | Formula-pinned adjusted-PIT chips; no claims or confirmation |
| R14 CA/sponsor PK reconciliation | PARTIAL | |
| R15 Scanner Lab UI | IMPLEMENTED SHELL / GUIDANCE ONLY | Runtime bundle includes native run, formulas, metrics, suppression and lineage; wider workspace remains open |
| R16 PIT before performance UI | PARTIAL | Fixture PIT contracts + UI lock; no production PIT dataset |
| R17 OpenAlgo live RO shadow | PARTIAL | Boundary only; capability `ABSENT` |
| R18 model governance / upgrades | PARTIAL | Drift assessment contracts only |

### Explicitly not implemented (do not over-claim)

1. Durable Q5 `selection_state_events` / PIT outcome storage (needs migration approval).
2. Production selection scan create/run APIs (`API-001` vertical).
3. Live-universe CONFIRMED with `productionAuthorized=true`.
4. Intraday CONFIRMED (blocked by Q5-R7).
5. MCX CONFIRMED (blocked; even good fixtures stay WATCH/WAIT ceiling).
6. PK production vote, sidecar or `/api/v1/shadow/pkscreener/*` routes (correctly absent).
7. Scanner Lab UI, pipe DSL, full native PK catalog.
8. Performance/probability UI (correctly locked).
9. Execution, OMS, account/position/margin routes (rejected and absent).

### Requirement-family summary

| IDs | Status |
|---|---|
| `GOV-001..006` | IMPLEMENTED at governance ceiling |
| `STA-001..004`, `STA-007` | IMPLEMENTED on fixture path; durable history missing |
| `FUS-001..008`, `FUS-011` | IMPLEMENTED in resolver; not sole legacy-rank path |
| `DAT-001..005` identity/PIT | PARTIAL Ã¢â‚¬â€ strong in Q5 contracts; not universal |
| `DAT-010` feature registry lint | IMPLEMENTED at R0 contract ceiling; 39 exact contracts, route-aware lint and read-only API |
| `DAT-011` pinned indicator engine | IMPLEMENTED at R0 contract ceiling; one run pin with warm-up/runtime/parity fail-closed checks |
| `DAT-015` MWPL owner freeze | IMPLEMENTED at split-contract ceiling; percentage artifact unavailable |
| `DAT-016` MCX master | PARTIAL (fixture gates) |
| `DAT-017` broker integrity | PARTIAL (boundary only) |
| `SEL-001..010` S0Ã¢â‚¬â€œS9 | PARTIAL |
| `PRF-001..007` | PARTIAL |
| `UI-001..006`, `UI-010` | IMPLEMENTED (fixture-backed) |
| `UI-007` Scanner Lab | IMPLEMENTED / GUIDANCE ONLY |
| `UI-009` PIT performance | Lock IMPLEMENTED; charts not productized |
| `STO-001..014` | PARTIAL Ã¢â‚¬â€ Q5 history/PIT not durable |
| `API-001..018` | PARTIAL Ã¢â‚¬â€ fixture GETs + OpenAlgo capability |
| `OPN-001..004` | IMPLEMENTED disabled boundary |
| `PK-001..016`, `PK-019` | PARTIAL Ã¢â‚¬â€ offline harness only |
| `PST-001..008` | POSTPONED as planned |
| `REJ-001..012` | REJECTED and excluded as planned |

### Immediate next work (File A plan order)

1. Close R0 residual inventory compiler, jobs, source maturity and dataset-root
   fields,
   `CROSS-001/002/003/006/007/019/020`, and linked TDG/Hybrid rows.
2. After separate migration approval, implement durable selection storage;
   otherwise keep the in-memory ceiling explicit and block all
   persistence-dependent claims.
3. Complete R1/R2 live DTO and S0-S3 work, then residual R4/R6 source, PK,
   enrichment and tradability boundaries. Extend R3/R5/R7 only through their
   dependencies and retain WATCH/WAIT/REJECT-first behavior.
4. Complete CROSS-004/005/009/015: named profile sources, activation backlog,
   FX-role split and tradability fields.
5. Implement R8 native core scanners under evidence-family caps.
6. Implement R9 lifecycle, ORB and VWAP only on verified bars.
7. Implement R10 pipe DSL before R11/R12 live MCX and options timeline work.
8. Complete R13/R14 scanners and corporate-action/sponsor reconciliation,
   including TDG-GAP-026 event matching.
9. Implement R15 Scanner Lab only after upstream contracts are stable.
10. Build R16 point-in-time datasets before performance or probability UI.
11. Enable R17 live read-only OpenAlgo shadow only after integrity/replay tests.
12. Finish R18 model governance, drift, calibration, versioning and rollback.
13. Never implement H10 live execution without a new File A amendment.

No dependency install, database migration, source-registry/workbook change,
external write, broker access, deployment or trading action occurred in this
audit. Documentation only, plus re-observation of existing fixtures/tests.

## 2026-07-20 - Q5-R6 Repaired And Q5-R7 Read-Only Boundary Complete

The earlier Q5-R6 completion claim was reopened after adversarial review. The
repair is now verified at the fixture-only ceiling. Q5-R7 is also complete at
its `NO_INTRADAY_CONFIRMED` ceiling. Neither milestone authorizes performance
UI, probability UI, broker/account access, order placement or trading.

Q5-R6 repairs:

- CONFIRMED proof is derived from a resolved `ConfirmationContext` containing a
  closed bar, official point-in-time facts, independent evidence families and
  passed deterministic gates. Caller-supplied pass booleans cannot confirm.
- Candidate instances use an explicit transition matrix, terminal REJECT
  behavior, structure substates and stable order-independent event identities.
- Outcome labels, returns, excursions, availability and zero-cost `NO_ENTRY`
  behavior are derived from immutable closed-bar paths. The public fixture does
  not serialize internal entry, target or stop path evidence.
- Walk-forward, holdout and drift gates now require versioned, hashed artifacts
  bound to the exact outcome IDs or validation baseline. Loose pass flags and
  unlineaged drift scalars cannot approve or preserve validation.
- The primary dashboard has separate WATCH and WAIT filters, fails malformed Q5
  payloads closed to WAIT, places all eight decision questions in the selected
  candidate analysis area and keeps validation hidden unless PIT approval and
  production authorization both pass. Q5-R6 itself fixes performance visibility
  to false and labels the circular score as evidence strength, not probability.

Q5-R7 boundary:

- Added a disabled-by-default OpenAlgo capability state machine:
  `ABSENT | DISABLED | FIXTURE_VERIFIED | SHADOW_LIVE | REJECTED`.
- Added `GET /api/v1/integrations/openalgo/capability` with a fixed
  `NO_INTRADAY_CONFIRMED` ceiling, explicit blockers and four advertised
  read-only routes: history, option chain, option Greeks and batch option Greeks.
- Remote hosts, account access, write/order routes, secrets in responses and
  executable behavior remain rejected. Even `SHADOW_LIVE` cannot enable
  intraday CONFIRMED without separately verified replay integrity.

Observed verification:

~~~text
Q5-R6 + Q5-R7 focused backend tests                  77 passed
Q5-R7/OpenAlgo focused tests                         29 passed
complete backend suite                              474 passed
frontend behavior + acceptance                     135/135
Q5-R6 fixture endpoint                              HTTP 200
internal outcome paths exposed                         false
OpenAlgo capability endpoint                        HTTP 200
OpenAlgo state                                      ABSENT
intradayConfirmationAllowed                          false
productionAuthorized / executable            false / false
~~~

No dependency installation, database migration, source-registry/workbook
change, root-architecture change, external write, broker/account access,
deployment or trading action occurred. Durable operational history/PIT storage
still requires separate database-migration approval. Browser screenshot QA was
not rerun; frontend evidence is syntax, behavior and DOM-contract testing.

## 2026-07-19 - Q5-R6 Inspector, History And PIT Governance Complete

Q5-R6 is complete at its approved fixture-only ceiling. It adds a working
primary-radar explanation surface and hidden evidence inspector, deterministic
append-only state-history contracts, descriptive point-in-time outcome
observations, cost-sensitive PIT validation and drift governance. It does not
authorize production performance/probability UI, execution or trading.

Implemented:

- Added proof-gated `WATCH | WAIT | CONFIRMED | REJECT` transitions. Recoverable
  confirmation failures resolve to WAIT; CONFIRMED requires closed-bar,
  evidence-family, hard-gate, source-health and PIT proof.
- Added stable material event identity plus reconstructable ordered state
  history. The Q5 fixture records denied transitions, source corrections,
  confirmation, demotion and deterministic invalidation.
- Added versioned costs, entry policy, universe/bar/delisting lineage, cutoff,
  MFE/MAE and descriptive path states. `NO_ENTRY`,
  `INVALIDATED_BEFORE_ENTRY`, `DELISTED_OR_UNPRICED`, `DATA_INCOMPLETE` and
  right-censored rows cannot manufacture a win/loss observation.
- Derived calibration error, net expectancy, drawdown, false-confirmed rate and
  cost sensitivity from immutable outcomes; caller-supplied summary metrics are
  not accepted. Walk-forward and holdout artifacts are mandatory for fixture
  approval.
- Added baseline-timed drift assessment. Missing, invalid, future or excessive
  drift cannot auto-promote and demotes the validation boundary to research.
- Added `GET /api/v1/selection/fixtures/q5-r6` and frontend rendering for eight
  concise radar answers, hidden inspector tabs and append-only history.
- Removed legacy READY wording from user-visible research states, removed
  entry/stop/target from the primary selection surface, and labelled the manual
  journal as non-training, non-ranking, non-confirming and non-executing.

Observed verification:

~~~text
Q5-R6 focused backend tests                            48 passed
complete backend suite                               456 passed
frontend acceptance                                 133/133
selection-package Ruff lint                 all checks passed
selection-package Ruff format                    14 files clean
live fixture API                                      HTTP 200
radar/history/inspector state                     REJECT/REJECT/REJECT
performance/probability visible                    false/false
validation section                                      HIDDEN
productionAuthorized / executable                  false / false
~~~

The local API was observed on `127.0.0.1:8001`. Visual browser automation could
not be completed because the in-app browser runtime failed twice with a Windows
sandbox setup error. Static DOM-reference verification and live API observation
passed, but no screenshot-based completion claim is made.

No dependency installation, database migration, source-registry/workbook
change, root-architecture change, external write, broker/account access,
deployment or trading action occurred. State history and PIT data are fixture
contracts only; durable operational persistence remains unimplemented and would
require separate migration approval. Q5-R7 is the next milestone.
## 2026-07-19 - Q5-R5 Offline PK Compatibility Boundary Complete

Q5-R5 is complete at its approved ceiling: PKScreener is represented only by a
finite offline differential harness and sanitized fixture contract. There is no
runtime sidecar, production route, ranking vote, state authority or confirmation
authority.

Implemented:

- Added strict PK upstream-pin, fixture-manifest, sanitized-input, native
  scanner, shadow-observation, differential-artifact, review and native-promotion
  contracts under `trendforge_api/scanners/`.
- Added one fixed local JSON worker with one invocation, bounded input/output,
  timeout termination, sanitized environment and typed process/output failures.
  The worker cannot run arbitrary commands or load pickle, cache, source or
  executable artifacts.
- Kept current comparison evidence explicitly fixture-only and unverified. A
  VERIFIED upstream pin is rejected because no observed PKScreener adapter has
  been implemented; fixture parity cannot be misreported as upstream parity.
- Added stable raw/normalized/output hashes, commit/license/environment/native
  implementation provenance, field tolerances, discrepancy classes, reviewer
  state and native-only promotion controls.
- Added `ShadowObservation` with zero voting weight and false rank/state/confirm
  permissions. No `/api/v1/shadow/pkscreener/*` or other PK production route was
  added.
- Added a developer-only `python -m trendforge_api.scanners` fixture report and
  31 adversarial tests covering T-191, T-192, T-193, T-218, T-219 and T-220.

Observed verification:

~~~text
Q5-R5 focused compatibility tests                    31 passed
combined Q5 R1-R5 tests                              92 passed
complete backend suite                              408 passed
frontend acceptance                                 119/119
Ruff lint                                   all checks passed
touched-file Ruff format check                5 files formatted
Python compileall                                     passed
developer fixture results              MATCH and UNRESOLVED
fixture promotion status               REGISTERED_NOT_ACTIVE
PK/shadow production routes                              0
productionAuthorized / executable              false / false
~~~

Repository-wide `ruff format --check .` still identifies 20 unrelated
pre-existing files. All Q5-R5 touched Python files pass format validation.

No live PKScreener checkout or upstream execution was claimed. No dependency
installation, database migration, source-registry/workbook change, frontend
behavior change, root-architecture change, external write, broker access,
deployment or trading action occurred. Q5-R6 is the next milestone.
## 2026-07-19 - Q5-R2 Family Resolver Complete

Q5-R2 is complete with the required `WATCH`, `WAIT` and `REJECT` acceptance
ceiling. It does not emit `CONFIRMED`.

Implemented:

- Added a versioned family-resolution profile with explicit family weights,
  required families, required sources, completeness floor, WAIT ceiling and
  `corroboration_epsilon=0`.
- Added deterministic support/opposition resolution. Only the strongest eligible
  claim on each side of a correlation group is selected; weaker same-group
  claims are suppressed with reasons.
- Suppressed future, missing-fact, invalid-fact, missing-source, failed-source,
  non-directional, shadow, reference and experimental claims instead of turning
  them into votes or fabricated zero evidence.
- Aggregated family support and opposition separately, then calculated evidence
  strength as their profile-weighted difference. It remains labelled as evidence
  strength, not probability.
- Implemented `STA-007`: missing, blocked, stale, partial or insufficient required
  evidence maps to WAIT; only an explicit hard veto/invalidation maps to REJECT.
- Made hard veto dominate lower-priority WAIT gate generation.
- Added `GET /api/v1/selection/fixtures/q5-r2` with selected/suppressed claim
  IDs, correlation groups, family resolution, gate codes and deterministic
  candidate states.

Observed verification:

```text
Q5-R2 focused resolver/API tests            10 passed
combined Q5 contract/resolver tests         20 passed
complete backend suite                     336 passed
frontend acceptance                        119/119
Ruff lint                          all checks passed
Python compileall                            passed
observed Q5-R2 API                          HTTP 200
emitted states                        WATCH WAIT REJECT
corroboration bonuses                          {0.0}
```

No dependency installation, database migration, frontend behavior change,
source registry/workbook update, external write, broker access, deployment or
trading action occurred. Q5-R3 is the next milestone.


## 2026-07-19 - Q5-R1 Source, Identity And PIT Fixture Vertical Complete

Q5-R1 is complete as an additive contract and fixture milestone. It does not
claim production readiness and cannot emit an early `CONFIRMED` candidate.

Implemented:

- Added typed `SourceContract` and `SourceResult` models with explicit
  `STRUCTURED_OK`, `VALID_EMPTY`, blocked, rate-limited, timeout, wrong-content,
  partial, parse-failed, schema-changed, stale and not-attempted states.
- Enforced proof requirements for structured and valid-empty results: source
  contract version, parser/schema version, data date, point-in-time timestamps,
  immutable artifact hash and contract-defined empty semantics.
- Added stable instrument, bar, event, fact, claim, candidate and scan-run
  identities plus timezone-aware point-in-time lineage and revision metadata.
- Added the exact four-state public schema: `WATCH`, `WAIT`, `CONFIRMED`,
  `REJECT`. The Q5-R1 fixtures emit only `WATCH`, `WAIT` and `REJECT`.
- Added four deterministic fixture candidates covering discovery, unclosed-bar
  wait, an attempted early confirmation held at WAIT, and a hard-veto reject.
- Added `GET /api/v1/selection/fixtures/q5-r1`. Each candidate answers the
  primary-radar questions for discovery, change, support, contradiction,
  missing proof, freshness, next confirmation and invalidation.
- Kept evidence direction separate from trade direction. The fixture contract
  has no entry, stop, target, quantity, order intent or win-probability field.

Observed verification:

```text
focused Q5-R1 contract/API tests           10 passed
complete backend suite                    326 passed
frontend acceptance                        passed
Ruff lint                         all checks passed
Python compileall                           passed
observed fixture API                       HTTP 200
public states                 WATCH WAIT CONFIRMED REJECT
emitted states                       WATCH WAIT REJECT
early CONFIRMED                               absent
```

No dependency installation, database migration, source-registry/workbook
change, external write, broker access, deployment or trading action occurred.
The existing causal/demo UI remains a legacy compatibility surface; it was not
silently redefined by this additive milestone. Q5-R2 is the next milestone.


## 2026-07-19 - Q5-R0 Contract Freeze Complete

Q5-R0 is complete as documentation and contract work only. It does not make a
production-readiness claim.

Verified:

- Frozen contracts `PK-019`, `API-019`, `FUS-011`, `STA-007`,
  `DOC-ERR-001` and `TRC-056` are present with final authority in the Q5 plan.
- Recovered the immutable independent audit from complete prior session output.
  The restored artifact has `875` lines, `44,303` bytes and SHA-256
  `8355D2C129037505DD2D32773E5B643EDCE5BE7DB9F7B4EFA33256105895D6C7`,
  exactly matching the plan's provenance record.
- The closure ledger covers audit lines `1-875` without a missing range.
- Production code contains no `/api/v1/shadow/pkscreener/*` route.
- `PK-019` keeps PKScreener finite and offline, `FUS-011` keeps the
  corroboration bonus at zero, `STA-007` maps recoverable evidence failure to
  WAIT and hard veto/invalidation to REJECT, and `DOC-ERR-001` controls the
  `bar_versions` name.

No executable module, API, storage, source contract or architecture boundary
changed during Q5-R0. Q5-R1 is the next milestone.

## 2026-07-19 - Q5 Baseline Runtime Hardening

Completed before Q5-R0 implementation:

- Reproduced all three previously reported backend failures.
- Added bounded retry handling to `AsyncEndpointClient`, including bounded
  `Retry-After` handling for HTTP 429 responses.
- Added backward-compatible `statusCode`, `attempts` and `errorType` fields to
  `EndpointFetchResult`.
- Classified access-denied/CAPTCHA HTML as `WRONG_CONTENT` with
  `errorType=BLOCK_PAGE`; it remains non-scoring and distinct from valid empty.
- Repaired the point-in-time evidence fixture so its freshness expectation does
  not decay merely because the calendar advanced. Production staleness decay
  was not relaxed.

Observed verification:

```text
three reproduced regressions                 3 passed
related endpoint/evidence regressions       36 passed
complete backend suite                     316 passed
Ruff lint                              all checks passed
Python compileall                            passed
frontend acceptance                       119/119
frontend JavaScript syntax                   passed
```

Known repository-wide quality debt remains explicit: Ruff format check reports
21 pre-existing files, and full mypy reports 72 errors in 14 files, including
missing third-party stubs and existing typing defects. These were not caused by
the baseline repair and were not hidden or mass-formatted.

The research-state ceilings and no-execution boundary were unchanged. At this
baseline stage Q5-R0 was the next milestone; the repair was not a
production-readiness claim.

The initial Q5-R0 preflight verified all six controlling IDs in the
authoritative plan, confirmed no production `/api/v1/shadow/pkscreener/*`
route, and confirmed the `bar_versions` erratum. It initially stopped because
the immutable 875-line audit required by `TRC-056` was absent. The later Q5-R0
entry above records its exact hash-verified recovery and closes that gate
without weakening the traceability contract.

## 2026-07-17 - Successful Twelve-Route Screener Source Merge

Completed:

- Integrated the twelve live-verified routes through the existing
  `AsyncEndpointClient`, source catalog, immutable archive and scanner paths.
- Added daily NSDL FPI table availability to intraday market context.
- Added dated NSE shareholding evidence to symbol candidates.
- Added Nifty/Bank Nifty derivative variants to market context.
- Added three bounded CFTC SODA routes to delayed macro-event context.
- Rebuilt the source master workbook without linked/not-linked overlap.

Observed live result: `12` fresh `RAW_ARCHIVED`, `0` broken, `0` stale
fallback and `0` wrong-content responses. The screener snapshot remained
`RESEARCH_ONLY`; that is expected and correct. The new routes improve evidence
visibility and research ranking, but they do not relax source, freshness,
gate, risk or execution boundaries.

Current master inventory partition:

```text
MASTER_CURRENT                 370
ALL_LINKS_FROM_REPORTS         354
LINKED_SOURCES                 105
NOT_LINKED_SOURCES             231
SUPPRESSED_NOT_LINKED_DUPES     18
linked/not-linked overlap        0
```

Verification evidence:

- `data/reports/archive/2026-07-17_link_report_cleanup/successful_12_source_fetch_after_screener_merge_2026-07-17.json`
- `data/reports/archive/2026-07-17_link_report_cleanup/successful_12_screener_snapshot_check_2026-07-17.json`

Remaining: source-specific normalization and gate wiring for BSE SAST/NSDL
tables, formal CFTC parser promotion, licensed/broker intraday evidence, and
the separate authorized execution milestone.

Updated: 2026-07-15

## 2026-07-15 Macro/Event Source Batch

Added a bounded research-only batch for the 20 requested agri/weather/China/MCX
operational/regulatory/release-schedule sources:

```text
POST /api/institutional/macro-event-sources/fetch
GET  /api/institutional/macro-event-context/latest
```

Live bounded result: `13/20` sources archived as research context, `7/20`
remained fail-closed, latest snapshot `WAIT_PARTIAL_SOURCE`, completeness
`0.65`, `canUnlockReady=false`.

Current canonical inventory file:

```text
D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-14.csv
```

Current counts: `233` rows total, `45` fresh structured usable, `188` not fresh
structured.

## Current Milestone

Milestones 1/2/3/5 data-integrity and causal-scanner integration are in progress. The scheduled harmonic lifecycle, deterministic corporate-action adjustment, and BSE offer-XBRL lineage slices are complete.

## Completed In This Slice

- audited repository entry points, dependency files, API routes and existing tests;
- located and hashed the preserved 6,387-line master plan;
- confirmed baseline backend and frontend tests;
- added machine-readable classification for all 209 canonical saved URLs;
- added typed contracts for all active source descriptors;
- added `GET /api/source-contracts/coverage`;
- added fail-closed source coverage tests;
- added concise project operating/documentation files.
- added a deterministic offline daily/intraday candle generator and CLI;
- initialized/verified the local database and loaded `TFDEMO` into SQLite and Parquet.
- added a typed point-in-time causal evaluator for CAUSE, SPONSOR, STRUCTURE and FLOW;
- added signal-specific staleness decay, stale-context cap and future-evidence rejection;
- added shared-input independence penalties and post-penalty layer floors;
- added batch percentile ranking, Stage 1/Stage 2 separation and safety/source-trust overrides;
- added `POST /api/causal/evaluate`; all outputs remain read-only (`executable=false`).
- wired stored-candle scans through the causal evaluator and persisted the full evaluation with each candidate;
- added explicit WAIT gates when CAUSE, SPONSOR, or official confirmation is unavailable;
- added eight deterministic named-state scenarios covering READY, WAIT, REJECT, NO_TRADE, WAIT_DATA_WEAK, WAIT_FOMO and LOCKED_NO_TRADE;
- added `demo-decisions` CLI and `POST /api/demo/decision-scenarios/load`;
- added latest scan, shortlist, WAIT and rejected-candidate endpoints;
- added Ruff and mypy development dependencies, formatted the backend and resolved all reported lint/type defects.
- added versioned migration records and a `migrate` CLI command;
- replaced silent duplicate-candle ignoring with hash-based correction lineage;
- added deduplicated candle-quality records and strict OHLC geometry validation;
- added migration, candle-quality and candle-revision APIs.
- added normalized, point-in-time evidence claims from large deals, AMFI stock deltas, SEBI PIT/SAST rows and qualifying corporate events;
- excluded ESOP/inter-se/future-available rows from positive conviction;
- persisted hash-deduplicated claims and attached them to stored-candle scanner evaluations;
- added `GET /api/evidence/{symbol}` and source-row lineage in evaluated evidence.
- added chronological harmonic lifecycle evaluation for FORMING, COMPLETE, TRIGGERED, INVALIDATED, WIN_T1/T2/T3, LOSS and EXPIRED;
- added conservative same-bar target/stop ordering;
- added immutable lifecycle events, deterministic fixtures, CLI loader and lifecycle APIs.
- added reasoned general alerts with risk payloads and acknowledgement;
- added manual intraday/swing journal records and outcome updates;
- added lifecycle-to-alert integration and rejected broker-order fields at the API boundary.
- exposed alert acknowledgement and manual journal creation/outcome controls in the dashboard;
- verified the operational UI against persisted records at desktop and mobile breakpoints.
- connected stored-candle scheduler scans to stable XABCD-derived harmonic pattern keys;
- persisted progressive lifecycle transitions and reasoned alerts without duplicate rerun events;
- added fail-closed timezone, level, chronology and revised-sequence conflict handling;
- corrected PRZ geometry to cluster around D instead of incorrectly spanning the full C-D leg.
- added corporate-action ratio, class, cash amount and revision extraction;
- added point-in-time NSE/BSE mirror reconciliation with cancellation and ratio-conflict detection;
- added ingestion-time split/bonus price and inverse-volume adjustment metadata;
- added migration `0006_corporate_action_adjustment_lineage` and persistent assessments;
- blocked harmonic analysis before pivots when known actions are unresolved or unadjusted;
- added explicit late-filing reconciliation through the existing candle revision ledger;
- exposed reconciliation and adjustment-lineage APIs and the gate reason in dashboard metrics.
- added cash-dividend reference-close adjustment and rights TERP adjustment;
- limited inverse-volume reconstruction to share-count actions (split/bonus);
- excluded contextual non-adjusting events such as buybacks from OHLCV integrity vetoes.
- added official NSE daily-buyback resolution with valid-empty semantics and immutable raw-archive lineage;
- added official BSE buyback/open-offer index resolvers while keeping list output metadata-only;
- added bounded linked-XBRL ingestion with XML entity/DTD rejection, schema guards, source dates, SHA-256 lineage and revision history;
- added migration `0007_bse_offer_xbrl_lineage`, normalized offer events, read-only APIs and dashboard drilldown;
- mapped current offer terms into one deduplicated contextual CAUSE claim per offer without allowing the event to independently unlock `READY`.
- added explicit merger/demerger reconstruction terms, same-symbol continuity validation and migration `0008_corporate_reconstruction_terms`;
- blocked ratio-only, conflicting and cross-symbol schemes while allowing a verified explicit same-symbol factor to adjust price without inventing volume changes.
- added persisted safety events, manual panic lock, recovery checklist, loss-streak cooldowns, daily soft/hard loss states and migration `0009_safety_state_events`;
- applied server-derived safety state to scanner candidates and position sizing so direct API/scanner calls cannot bypass the dashboard lock;
- added total open-risk, sector-risk, portfolio-correlation and MCX-position caps while preserving deterministic stop-risk sizing;
- replaced the browser-only lock toggle with persisted panic/recovery APIs and a five-item recovery dialog.
- added official NSE equity-master and Nifty 500 constituent resolvers, parsers, raw archives and normalized point-in-time identity/industry tables;
- added migration `0010_nse_instrument_universe` and live-verified 2,384 instruments plus 500 Nifty 500 memberships;
- added deterministic Nifty trend/DMA, India VIX, breadth/narrow-rally and sector RRG classifiers with point-in-time/freshness vetoes;
- added migration `0011_market_sector_context`, read-only context APIs, scanner `MARKET_CONTEXT`/`SECTOR_CONTEXT` gates and dashboard context/universe status;
- corrected a live-only parser defect where the first listing date was mistaken for file date; parser v1.0.1 prioritizes HTTP Last-Modified and invalid rows were retained as inactive audit lineage.
- added official NSE segment holiday resolution through `holiday-master?type=trading`, immutable raw archival, structured annual coverage and migration `0012_nse_trading_calendar`;
- made background scans fail closed on missing calendar coverage, holidays and weekends while preserving explicit manual research runs and explicit special-session support;
- exposed calendar status/day APIs and the live NSE session state in the dashboard command bar;
- replaced the remaining silent harmonic Parquet exception with structured error logging and a visible response warning.
- added official NSE CM UDiFF and all-indices EOD parsers, normalized cash/index tables and migration `0013_nse_official_market_context_inputs`;
- added bounded one-year archive bootstrap with content-addressed raw lineage, direct-only fetches and no catalog-page fallback;
- automated Nifty 20/50/200-DMA, India VIX, same-date breadth and ten sector-index context snapshots;
- made EOD freshness NSE-session aware with an 18:00 IST publication cutoff instead of a naive weekend wall-clock timeout;

## Current Verified Baseline

```text
Backend baseline before this source-audit slice: 162 passed in 35.61s
Ruff lint: all checks passed
Ruff format check: 85 files formatted
Mypy: success, no issues in 67 source files
Python compileall after this slice: passed
Frontend after this slice: 95/95 checks passed
New targeted source-contract tests: 2 passed
Source coverage: 211/211 URLs classified; 30/30 active sources contracted
Database CLI: integrity ok, foreign keys on, WAL
Demo CLI: 160 daily + 750 five-minute candles plus 30m/1h/4h_custom/1d/1w derived series, executable=false
Live runtime: health ok on 127.0.0.1:8001; source coverage 209/209 and 25/25
Browser smoke: no console errors and no horizontal overflow at the active 1137px viewport
Operational UI smoke: one persisted alert and journal record loaded; acknowledgement and synthetic journal creation succeeded
Responsive geometry: no horizontal overflow at 390px; all three workspace regions expand to the mobile content width
NSE resample live smoke: 20 custom-4h bars from 10 sessions; 10 explicitly partial; zero warnings
Named-state CLI: run 6, 8 candidates, executable=false
Live named-state endpoints: latest=8, shortlist=1, WAIT=3, rejected=4
Dashboard named-state flow: 8 rendered radar cards, no console errors, no horizontal overflow
Migration CLI: PASS, versions 0001 through 0006 applied
TFDEMO quality lineage: 1,143 WARN records (synthetic/research-only), 0 false revisions after identical reload
Scheduled lifecycle focused tests: 3 passed; stable key, progressive events, dedupe and revision conflict covered
Current-database scanner smoke: run 8 COMPLETE, 2 candidates, official source gates blocked, executable=false
Corporate-action focused tests: 8 passed, including dividend, rights, late-filing pre-harmonic veto and revision-ledger recovery
Current-database corporate-action smoke: run 9 COMPLETE; seven TFDEMO assessments persisted as PASS with zero known actions
Live corporate-action APIs: migration 0006 visible; reconciliation remains executable=false
Dashboard corporate-action metric: PASS/reason rendered, zero console errors, no horizontal overflow
Migration CLI after reconstruction work: PASS, versions 0001 through 0008 applied
Official NSE daily-buyback snapshot: structured valid-empty `data=[]`, data date 2026-07-11, archived SHA-256 `8fe32e407a1038ee38753b70e5374b3a46d6ae9d5f16cd5b73c53abaca8f5ed0`
Official BSE indexes: 76 buyback rows dated 2026-07-07 and 157 takeover rows dated 2026-07-08; both remain metadata-only until linked XBRL terms parse
Official BSE XBRL proof: TEAMLEASE buyback PRE terms at INR 1,600 for 1,487,500 shares and Senthil Infotek POST offer terms at INR 8; raw documents archived by hash
BSE offer APIs: documents=2, current events=2, latest detail parser state `PARSED_STRUCTURED`, every response `executable=false`
BSE dashboard drilldown: state, phase, anchor, quantity, revision and hash rendered with `Trade Role: CONTEXT_ONLY`; zero desktop/mobile console or overflow defects
Migration CLI after safety work: PASS, versions 0001 through 0009 applied
Live safety API: `GREEN`, risk multiplier 1.0; no panic lock was inserted into the user's live database during validation
Safety scanner test: persisted panic state forced `LOCKED_NO_TRADE` and saved `TRADER_SAFETY` gate decisions
Safety dashboard: server state `GREEN`, five recovery acknowledgements present, zero console errors, no desktop/mobile horizontal overflow
Source coverage after universe additions: 211/211 URLs classified; 27/27 active sources contracted
Official NSE equity master: HTTP 200, 168,316 bytes, SHA-256 `6b1a9adb38c92a3b61a085dfc8e7ccbb61c54ffe81d322e5c7293944495ed222`, data date 2026-07-09, 2,384 rows, `STRUCTURED_OK/FRESH`
Official Nifty 500 membership: HTTP 200, 32,766 bytes, SHA-256 `f9938da0fd227cefece7451bd6b18d7aa4b39945a3f904d4aebda295fe2b3dda`, data date 2026-07-11, 500 rows, `STRUCTURED_OK/FRESH`
Live migrations: 13 versions, PASS; live universe endpoint: 2,384 instruments / 500 Nifty 500 memberships
Official NSE trading calendar: HTTP 200, 33,691 bytes, SHA-256 `798c545acc5351eb9ed84f353c1fcc665a26967426e3761b7097e7f3c7042424`, 237 segment records, 20 CM closures, 2026 annual coverage
Calendar runtime on 2026-07-11: `CLOSED_WEEKEND`; scheduled scan blocked, manual research remains explicit; dashboard desktop/mobile has no overflow or console errors
Official context runtime: 220 Nifty sessions, 220 VIX sessions, 2,370 EQ breadth rows, `RANGE / SOFT_FAIL`, India VIX 12.25 NORMAL, breadth 2.9696
Official context dashboard: `220 sessions`, `RANGE`, `12.25 NORMAL`; zero desktop/mobile console or overflow defects
Cached Nifty 50 benchmark: 50 official-current symbols, 11,000 deterministic cached candles, 50 candidates, 10.2058-second scan, target under 30 seconds, PASS, executable=false
Source health contract: source authority, latest data date, last attempt, last successful fetch, consecutive failures, stale threshold and source limitation are exposed; no implicit demo health in normal mode
Final runtime: PID 26728 on `127.0.0.1:8001`; 30 operational source rows; NSE cash/index and F&O UDiFF EOD green at 2026-07-10; no demo candidate in normal mode
Final browser: RANGE, India VIX 12.25 NORMAL, CLOSED_WEEKEND; zero console warnings/errors and zero horizontal overflow at desktop and 390px mobile
Official NSE F&O UDiFF: HTTP 200, 1,151,276 bytes, SHA-256 `2933ae94177caa455aefaea1c95caf3c1b2e95c2ad8cd8de1746919605e870a2`, one CRC/hash-verified CSV member, data date 2026-07-10, 36,565 structured rows, snapshot 309 / parse 320
Artifact-integrity boundary: empty, length mismatch, manifest mismatch, HTML masquerade, malformed ZIP, unsafe path, CRC/container and decompression limits fail before parser normalization; nine focused tests pass
Storage initialization: schema/source seeding is process-idempotent per database path; profiling removed 957 redundant initialization calls from a 50-symbol scan without weakening migration checks
Source-analysis input: all 1,552 lines / 10,957 words audited; SHA-256 `878b43c1d3485dce98bd4096103c010ac89090b502cb41ffd09722268a0648ae`
Official F&O ban: `fo_secban.csv`, trade date 2026-07-13, exact symbol `KAYNES`, integrity PASS; ban is a hard veto while G13 remains `WAIT_MWPL_PERCENTAGES`
Official NSE bulk deals: 8,200 bytes, SHA-256 `ceb35ff252c1fdc03531d26a8fe4f773b55511786c2f0c21f629466204122816`, data date 2026-07-10, 89 rows, snapshot 310 / parse 321, integrity PASS
Official CFTC COT: 1,306,533-byte 2026 archive, SHA-256 `7733ce1d4ba953e96206f3e1393150734f871a231b9350262910de5b66252806`, report date 2026-07-07, 10 relevant rows, snapshot 311 / parse 322, integrity PASS
OpenAlgo read-only client: documented history and option-chain POST contracts implemented; localhost/env-only boundary, no order methods, live credentials still pending
Final source-audit verification: 174 backend tests passed in 37.83s; Ruff lint and format passed; mypy passed for 68 source files; compileall passed; frontend 95/95 passed
Final runtime: PID 13552, health `ok`, guarded-research mode on `http://127.0.0.1:8001/`; KAYNES G13 is `BLOCKED_FNO_BAN`; next-session ban freshness is valid
Final dashboard smoke: market regime loaded as `RANGE`, no console errors/warnings and no horizontal overflow at 1248px
```

## Known Limitations

- Most official sources remain fixture-tested or live-unverified.
- No legal live NSE/MCX intraday feed is connected.
- OpenAlgo is not connected.
- OpenAlgo client contract is built and tested, but no broker session or live credentials have been supplied.
- Official MWPL percentage, SLB and MCX bhavcopy direct artifact contracts remain unverified; guessed 404/HTML URLs were removed.
- Current frontend is static JavaScript, not React/TypeScript; it is preserved because the repository is not empty.
- Evidence mapping currently covers core structured rows but not news, earnings fundamentals, delivery absorption, policy events or cross-market drivers.
- Ratio-only, cross-symbol and complex merger/demerger reconstructions remain blocked until deterministic official terms and instrument-lineage models are implemented.
- Cross-symbol merger/demerger history remains blocked pending a separate instrument-lineage series builder; only explicit same-symbol continuity is currently reconstructable.
- BSE linked-XBRL ingestion is bounded/manual; full historical backfill and scheduled detail refresh are not yet implemented.
- Official Nifty/VIX/breadth and sector-index EOD ingestion is connected; legal live intraday market context still requires OpenAlgo or another licensed feed.
- Application remains read-only and guarded research only.

## Next Work

1. connect OpenAlgo through the existing licensed-feed boundary after credentials are provided;
2. replace remaining fixture-only official parser paths with live-verified artifacts;
3. add cross-symbol instrument lineage before any merger/demerger series stitching.

## 2026-07-12 Trade Vision And OpenAlgo Integration

Implemented:

- added a read-only OpenAlgo OHLCV adapter for broker-connected historical candles;
- matched OpenAlgo's actual `/api/v1/history` contract, including `D` daily tokens;
- kept OpenAlgo credentials environment-only and blocked remote hosts by default;
- added `GET /api/integrations/trade-vision/evidence/latest`;
- exported the complete latest scanner run with candidates, gates, source lineage,
  command-bar state, packet SHA-256 and HMAC signature;
- made every export explicitly research-only and non-executable;
- live-tested TrendForge to Trade Vision intake on loopback with an ephemeral secret.

```text
TrendForge backend                         181 passed
OpenAlgo/Trade Vision focused contracts   22 passed
Signed packet                             accepted
Candidates transported                    2
Candidates eligible for review            0
OpenAlgo handoff allowed                   false
Broker order created                       false
Live trading blocked                       true
```

Failure-path proof: a newer scanner run that raised an exception was finalized
as `ERROR` with a finish timestamp. The evidence exporter ignored both ERROR
and RUNNING records and continued exporting the most recent `COMPLETE` run.

OpenAlgo order submission is deliberately not part of TrendForge. The current
candidates failed source/causal gates and had no valid entry/stop/target
package, so forwarding them as orders would violate the fail-closed contract.

## 2026-07-13 Optional VYOM Source Discovery

Implemented an optional Crawl4AI/VYOM fallback for dynamic catalog link
discovery. Direct artifacts and static HTML discovery remain primary. VYOM
links are candidate-only, are independently re-fetched by TrendForge, and have
no authority to unlock `READY`.

Added a persistent `source_fetch_attempts` ledger and
`GET /api/source-fetch-attempts` so every attempted URL, fetcher, stage, HTTP
status, content type, byte count, duration and error can be audited.

Controlled live checks covered NSE SLB, AMFI portfolio/scheme disclosures,
SEBI PIT/SAST and MCX bhavcopy. VYOM rendered three catalogs but found no
schema-valid direct artifact; MCX exposed no usable links. All four structured
parsers remained correctly blocked. Full evidence is in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S015`.

Final verification: 185 backend tests passed, Ruff lint/format passed, mypy
passed for 70 source files, compileall passed, and frontend acceptance remained
95/95. Runtime PID 23772 is serving the updated guarded-research app on
`http://127.0.0.1:8001/`; the attempt-ledger endpoint returned two persisted
NSE SLB attempt rows.

## 2026-07-13 Deterministic 211-Link Audit And Clean Data Slice

Implemented a bounded source-inventory audit that records all 211 saved URLs on
every run while fetching only explicitly selected IDs. It canonicalizes URLs,
detects duplicates, tries official direct candidates before landing pages,
profiles CSV/JSON/ZIP/HTML payloads, archives bytes by SHA-256 and persists both
run-level and row-level evidence. Audit output is never gate authority.

Added strict FRED parsers for 10-year real yields (`DFII10`) and the broad dollar
index (`DTWEXBGS`). The live production pipeline persisted 5,883 and 5,139
numeric observations respectively. Real yields are fresh at 2026-07-09; the
dollar series is visibly stale at 2026-07-02. Neither can independently unlock
`READY`.

```text
latest audit run                    b9542aaecca3427e95e54958662ac837
inventory rows recorded             211
selected network fetches            6
tabular candidates                  2
JSON candidates                     4
new migrations                      0015 and 0016
backend                             201 passed
frontend                            95/95 passed
lint/format/mypy/compileall         passed
```

Full performed-link evidence is in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S012`.

## 2026-07-13 Full Pending-Link Audit And Three Source Activations

Network-audited all 146 official rows that remained in the activation-review
set. The row-level result is
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S010`; it records fetch state,
resolved artifact, hash/path, conversion state, limitation and required work.

```text
EIA weekly petroleum     19 metrics, data date 2026-07-03, delayed context
MCX bhavcopy             143 futures rows, data date 2026-07-10, EOD only
NSE SLB                  235 symbols, data date 2026-07-13, proxy only
CFTC COT refresh          10 rows, data date 2026-07-07, weekly delayed
NSE F&O refresh       36,565 rows, data date 2026-07-10, EOD only
```

The MCX parser accepts only `FUTCOM` rows because options require a separate
strike-aware schema. SLB parsing aggregates settlement series per symbol and
does not mistake outstanding quantity for trading volume.

Final verification: 212 backend tests passed; Ruff lint/format, mypy for 73
source files and compileall passed; frontend acceptance passed 95/95. Runtime
PID 13008 is healthy on `http://127.0.0.1:8001/`. Public API drill-down returned
persisted rows for all five refreshed contracts.

## 2026-07-13 AMFI Scheme-Wise API Activation

Implemented the official AMFI directory/API resolver and a separate quarterly
exposure contract. The live run archived snapshot 374 and accounted for all 56
fund IDs: two funds returned 460 source rows and 54 returned explicit official
`Nil` responses. Parser output 396 is structured and dated 2026-03-31.

All 460 rows are persisted in `amfi_scheme_exposure_rows`. No monthly quantity
delta was created. Company names are not treated as NSE symbols; ISIN mapping
is still pending. `amfi_monthly_portfolio` remains unactivated because actual
monthly per-AMC workbooks are not yet normalized.

Core-link status and corrected classifications are in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S013`.

Runtime PID 19180 serves the updated guarded-research application at
`http://127.0.0.1:8001/`; health is `ok` and the AMFI parser endpoint returns
`PARSED_STRUCTURED`, data date 2026-03-31 and 460 rows.

## 2026-07-13 FII/DII And AMFI NAV Activation

Activated official `nse_fii_dii` and `amfi_nav` contracts. Live snapshots 375
and 376 produced two institutional cash-flow rows dated 2026-07-13 and 14,216
NAV observations through 2026-07-12. Both raw artifacts are hash archived and
their normalized rows are locally persisted.

AMFI NAV is reference-only and NSE FII/DII is market-regime-only. BSE bhavcopy
HTML, empty option-chain JSON and empty PIT output remain blocked. Full result:
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S014`.

Runtime PID 16864 is healthy at `http://127.0.0.1:8001/`; both new parser
result endpoints return `PARSED_STRUCTURED` with 2 and 14,216 rows.

## 2026-07-13 Supplemental Endpoint Monitoring

Added four non-destructive monitored contracts. `nse_block_deal_live` stored one
dated context row. `nse_option_chain` and `nse_pit_current` currently report
`NO_DATA_NOW`. `bse_bhavcopy_eod` reports `WRONG_CONTENT_NOW` because the saved
response is HTML. All responses are archived and visible; a later valid payload
will be normalized automatically without relaxing trade gates.

Final verification: 229 backend tests and 95/95 frontend checks passed. Ruff,
format, mypy and compileall passed. Runtime PID 33016 is healthy on
`http://127.0.0.1:8001/` and exposes all four current endpoint states.

## 2026-07-13 Surveillance, Pledge, OI-Spurt And NSDL Activation

Audited the submitted nine-source fetcher against live payloads and integrated
five new official contracts: `nse_asm`, `nse_gsm`, `nse_pledge_data`,
`nse_oi_spurts` and `nsdl_fpi_daily`. Existing FII/DII, PIT, option-chain and
AMFI NAV contracts were retained rather than duplicated.

```text
NSE ASM                       185 rows (145 long-term, 40 short-term)
NSE GSM                         0 rows, valid dated official empty list
NSE promoter pledge         1,532 rows preserved, 1,529 company names
NSE OI spurts                 215 rows, activity context only
NSDL FPI                       34 typed rows (25 cash/debt, 9 derivatives)
registered contracts           43
fresh structured contracts     24
```

G03 now requires fresh ASM and GSM source states. A clean symbol passes; a
listed symbol receives `BLOCKED_SURVEILLANCE`. Valid official empty GSM is not
treated as a fetch failure. Pledge rows remain delayed and company-name based,
OI spurts cannot calculate MWPL, and NSDL remains aggregate regime context.

The frontend parser drilldown exposes all nine submitted source families. Raw
bytes, parser outputs, freshness, normalized domain rows and exact source scope
are locally retained. Full evidence is in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S014`.

Runtime PID 12992 is healthy at `http://127.0.0.1:8001/`. The live catalog
returns 43 contracts, an ASM sample returns `BLOCKED_SURVEILLANCE`, RELIANCE
returns G03 `PASS`, and all five new domain drilldowns return rows or a valid
empty state.

## 2026-07-13 Gold And Physical-Market Context Activation

Activated four official structured contracts with immutable raw lineage:

```text
WGC gold open interest          1,256 rows, data date 2026-07-10
WGC ETF holdings               5,839 rows, data date 2026-07-10
WGC ETF flows                  2,225 rows, data date 2026-07-10
SGE daily market report           17 rows, data date 2026-07-13
registered source contracts       48
```

LME warehouse stocks and MCX delivery reports are registered and visible but
remain access-blocked. The new inputs enrich MCX context without relaxing the
core pass set. `MCX_CONTEXT` remains `WAIT_SOURCE_SNAPSHOT` until synchronized
USD/INR evidence exists. Full evidence and corrected source assumptions are in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S016`.

Final verification: 248 backend tests and 95/95 frontend checks passed. Ruff
lint/format, mypy for 80 source files and compileall passed.

Runtime PID 27516 is healthy at `http://127.0.0.1:8001/`. Live API checks
returned 48 catalog contracts, four fresh gold-context contracts and normalized
domain rows for every newly activated source.

## 2026-07-13 Institutional Multi-Factor Build

Added a config-driven institutional research subsystem without weakening the
existing fail-closed scanner. It includes 37 endpoint contracts, async raw
archival, typed feature calculation, model capability/readiness states,
Isolation Forest anomaly gating, weighted factor classification, INR 1 lakh
risk sizing, walk-forward validation, SQLite audit reports and a compact
frontend panel.

Public API clients cannot set their own source/model readiness. All outputs are
read-only. The current model registry is untrained, so this layer cannot yet
authorize a production `READY` result.

```text
focused institutional tests             17 passed
full backend suite                      265 passed
frontend acceptance                104/104 passed
Ruff lint/format                         passed
mypy                                 87 files passed
compileall                               passed
live endpoint contracts                       37
raw archived                                  20
no data now                                    6
broken                                         9
wrong content                                  2
```

Live runtime proof: PID 24868 is healthy at `http://127.0.0.1:8001/` in
guarded-research mode. Responsive browser QA passed on desktop and 390x844
mobile layouts with no horizontal overflow or console errors. Docker image
build verification remains pending because the Docker CLI is unavailable on
this workstation.

## Source Documentation Consolidation - 2026-07-14

The 21 active link/API artifacts were consolidated into the single AI-facing
`TREND_FORGE_SOURCE_REGISTRY.md`. It contains 21 deterministic segments and
27,833,447 bytes of original content. Every embedded segment was checked
against the SHA-256 of its source file before any source file was moved.

The 20 superseded files from `docs/` were moved, not erased, to
`delete/source_link_api_merge_2026-07-14/`. The active `docs/` directory now
contains only the five general project documents. Runtime evidence under
`data/reports/` remains untouched.

## 2026-07-15 Priority Source Adapter Build

Implemented current BSE UDiFF CSV/ZIP parsing, exact AMFI position deltas, and a
new persisted commodity-context subsystem for MCX options, SGE gold benchmark
and Baker Hughes rig counts. Added a read-only API and frontend MCX context panel.

Current bounded results: NSE EOD 2,382 rows; BSE EOD 4,857 rows; AMFI
scheme-wise 460 rows; MCX option chain 332 normalized stale rows; SGE 4,974
observations; Baker Hughes report date 2026-07-10. MCX and Baker fresh attempts
failed and remain explicit stale fallback. AMFI monthly portfolio remains valid
empty/no signal because its landing page did not expose stock-holding rows.

The canonical URL inventory now has 215 rows: 45 fresh structured, 2 stale
structured, and 168 in other non-fresh classifications. No source in the new
commodity subsystem can unlock READY.

Runtime is healthy at `http://127.0.0.1:8001/`. The dashboard displays MCX
option positioning, SGE trend and Baker Hughes supply context with their actual
fresh/stale states and explicit research-only limitation.


---

## 2026-07-16 Scanner Parser Link Update

Fresh structured usable inventory links increased from 45 to 47 after the 13-source scanner parser verification. BSE block-deal rows now have fresh structured evidence. Live verification summary: 13 sources fetched, 8 raw archived fresh, 4 valid empty, 1 stale fallback, 0 broken, 3176 normalized disclosure events. Canonical current files are `D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-16.csv` and `D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-16.xlsx`.

## 2026-07-28 FMR-011 Paper Lab and ML Learning Plan Registration

`FMR-011` now specifies a local deterministic Research Paper Lab, objective
path-derived outcomes, immutable PIT training examples, offline batch challenger
training, drift monitoring, human model promotion and rollback. It maps to R15,
R16 and R18. File A now permits this no-broker research replay while continuing
to reject broker-connected paper/live trading, executable quantity, external
side effects and automatic model promotion.

Current code already contains manual journal and ML snapshot primitives. The
Paper Lab, objective outcome worker, training-dataset builder, challenger
trainer, model registry/promotion workflow and learning inspector are **planned,
not implemented**. No runtime/frontend behavior changed in this documentation
milestone.

## 2026-07-30 Professional Mathematics Documentation Reconciliation

The professional trade-decision mathematics reference was reconciled with File
A, Hybrid, Final Merge, Discovery, the full architecture and lasting decisions.
This was a documentation/governance milestone only.

Completed corrections:

- generalized expected value to conditional gain/loss/cost distributions and
  added conservative probability, payoff and cost bounds;
- separated infinite-horizon first-passage math from finite-horizon
  target-before-invalidation research, including no-hit-by-horizon outcomes;
- corrected factor residuals to subtract alpha plus aligned market and sector
  exposure;
- retained the current evidence-based CONFIRMED state while keeping
  probability/EV unavailable until mapped R16/R18 PIT validation;
- replaced active OI intent labels with the four observable price/OI codes;
- kept File A FUS-009, Hybrid q_i, Discovery M-Factor and Final
  Merge/Options formula ownership separate;
- marked covariance fusion, microprice, OFI and calibrated impact as research or
  unavailable pending source and validation proof;
- registered File A section 25.22 and decision D-030 without creating a second
  build order;
- expanded the existing changed-file allowlist and structural validator for the
  mathematics, Hybrid and root architecture documents.

Observed documentation validation: 26 focused governance tests passed; coverage
remained 155 rows with zero additions, removals or changes; the protected runtime
manifest remained
643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D.
No backend/frontend runtime source, source activation, workbook, database,
broker boundary or scanner behavior was changed. Probability/EV UI,
microstructure features and production-readiness claims remain unavailable.
## 2026-07-30 - Theta, delta-hedged variance and VRP documentation reconciliation

**Status:** Documentation and governance contracts reconciled. No runtime scanner, source activation, probability, quantity, execution or production-readiness claim was added.

Completed:

- Professional Mathematics sections 17.5-17.7 now own complete dividend-aware call/put Theta, local delta-hedged realized-versus-implied variance attribution, and same-horizon variance-risk-premium research context.
- File A maps the work to R12/R16, with R18 only for future promotion/drift governance. Final Merge, Hybrid, Discovery, Options, root architecture and D-030 now carry the same boundaries.
- Hidden-inspector outputs are limited to modeled attribution and `IV_RICH_CONTEXT`, `IV_CHEAP_CONTEXT` or `VRP_UNKNOWN`; options context cannot own direction, public state, quantity or execution.
- Fixed VRP thresholds, `IV > RV => sell`, `IV < RV => buy`, guaranteed gamma-scalping profit and directional conclusions from backwardation/contango are rejected.
- Remaining-build navigation and `fileindex.md` point builders to Professional Mathematics sections 17.5-17.7 for mapped R12/R16/R18 work.
- Structural governance now requires the formulas/cross-references and includes traps for missing `VRP_UNKNOWN` handling and unsafe automatic VRP trade commands.

Observed verification:

- `python -m pytest docs\fable\remaining_build\test_build_coverage_csv.py -q` -> `26 passed`.
- Coverage compiler -> `Rows: 155; added=[]; removed=[]; changed=[]`.
- Protected runtime manifest -> `643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D`, unchanged from baseline.

Remaining implementation boundary:

- R12 has not implemented a scanner-ready VRP feature through this documentation change.
- R16 still must prove synchronized PIT implied/expected-realized variance, costs and calibration.
- R18 still owns any future model promotion, drift, demotion and rollback.
- Until those gates pass, runtime presentation must remain unavailable or `VRP_UNKNOWN` and cannot publish automatic option-buy/sell guidance.

## 2026-07-30 - Options and VRP readiness clarification

The staged `R0 -> R12 -> R16 -> R18` approach is verified as a useful
architecture and safety sequence. It prevents stale, mismatched, proxy-only or
uncalibrated options evidence from being presented as scanner confirmation.
The existing governance checks prove that VRP ownership, fail-closed behavior,
`VRP_UNKNOWN`, anti-double-counting boundaries and runtime containment are
documented consistently.

This is not evidence of predictive trading value. Live option-timeline
ingestion, synchronized implied/expected-realized variance, point-in-time
calibration, realistic costs, out-of-sample performance, production APIs,
storage and frontend behavior remain unimplemented or unverified. Therefore
the specification is ready for sequential implementation, but the VRP/options
feature is not production-ready and cannot claim a higher win rate.

## 2026-07-30 - Conditional VRP research-proposal scope amendment

File A section 25.23, Professional Mathematics section 17.10, Options and
D-030 now permit a future hidden-panel, non-executable VRP research proposal
for a defined-risk position family, research lot count and hedge structure.
The amendment does not add runtime behavior. `R12`, `R16` and `R18` acceptance
plus complete data, cost, liquidity, stress and instrument inputs remain
mandatory; otherwise the required result is `NO_RESEARCH_PROPOSAL`.

No broker/account access, order intent, execution or public-state authority was
added.

## 2026-07-30 - Source-result freshness and valid-empty confirmation hardening

**Status:** Implemented and regression-verified at the existing R0 source-contract
ceiling.

Corrected runtime behavior:

- `VALID_EMPTY` remains distinguishable from failure and research-visible, but
  cannot support `CONFIRMED` and has a `WAIT` state ceiling.
- Successful structured parsing defaults to `UNKNOWN` freshness rather than
  being automatically promoted to `FRESH`.
- Only explicit `FRESH` proof plus `STRUCTURED_OK` and an approved source role
  can make a source result confirmation-eligible.
- Explicit stale proof converts an otherwise successful result to `STALE` with
  typed `STALE_SOURCE` error and a `WAIT` ceiling.
- The Q5 GSM valid-empty fixture was corrected from confirmation-capable to
  fail-closed `WAIT`.

Observed verification:

- focused source-result/source-hardening suite: **26 passed**;
- complete backend suite: **537 passed**;
- changed Python files compiled successfully;
- frontend contract/acceptance suite: **135/135 passed**.

This does not implement redirect manifests, migrate storage, activate a source,
verify a live endpoint or authorize production `CONFIRMED`.

## 2026-07-30 - Live populated source-data verification

The source catalog was retested using the implemented fetch, parse, normalize
and freshness pipeline. HTTP status alone was not counted as success.

Current observed result:

- catalog entries: **74**;
- parser-backed entries tested live: **39**;
- links returning populated normalized scanner data: **29**;
- structured links returning a valid empty dataset: **2**;
- unproven empty parses: **3**;
- metadata-only results: **3**;
- schema mismatches: **2**;
- catalog entries without a structured parser: **35**.

The 29 populated sources returned actual records such as equity symbols,
F&O contracts, OI, volume, bhavcopy prices, large deals, surveillance lists,
institutional flows, pledges, SLB, index constituents and macro/commodity
context. Examples included 31,284 NSE F&O bhavcopy rows, 2,390 NSE equity
universe rows, 213 NSE OI-spurt rows, 106 NSE large-deal rows, 191 ASM rows and
82 GSM rows.

The two valid-empty sources were `nse_daily_buyback` and `nse_fno_ban`. They
prove that the source contract and parser worked, but they did not provide a
stock or contract candidate in this run and are therefore excluded from the
**29 populated-data links**.

This live result changes neither source activation nor confirmation authority.
Global source activation remains false; none of these sources can independently
authorize production `CONFIRMED`.

## 2026-07-30 - AMFI valid-empty and BSE artifact hardening

**Status:** Implemented and live-verified through the existing source monitor,
raw archive, parser and SQLite persistence path.

- AMFI per-fund HTTP `200` JSON messages `Nil` and `No data found.` now count as
  contract-valid empty responses instead of schema failures. Other non-list
  payloads still fail closed.
- BSE download candidates are checked for HTML before `.csv` or `.zip` suffixes
  are trusted, preventing an HTML landing/block page from being archived as a
  usable market artifact.
- The official AMFI scheme-wise run accounted for all 56 published fund IDs:
  2 populated funds, 54 valid-empty funds, 0 failures and 440 parsed exposure
  rows for quarter end 2026-06-30.
- AMFI NAV remained `PARSED_STRUCTURED` with 14,217 rows dated 2026-07-30.
- BSE bhavcopy remained `PARSED_STRUCTURED` with 4,872 OHLCV rows dated
  2026-07-30 from the current UDiFF CSV.
- AMFI monthly portfolio remains `WAIT_EMPTY_PARSE` with zero holdings rows.
  It is not replaced by NAV or quarterly exposure and cannot imply stock-level
  monthly mutual-fund buying.

Verification: focused source tests **17 passed**, complete backend **540
passed**, frontend **135/135 passed**. This correction supplies parsed delayed
context and EOD data only; source activation remains false and no source gains
independent `CONFIRMED` authority.

## 2026-07-30 - Eight-source prototype reconciliation and BSE XBRL completion

The two supplied standalone prototypes were compared against the existing
TrendForge source pipeline. All eight source families already had native
contracts, so no duplicate downloader, output directory, database or
`curl_cffi` dependency was added.

Live source results through the existing monitor/parser/archive path:

- FRED broad-dollar index: 5,154 structured observations through 2026-07-24;
- FRED 10-year real yield: 5,896 structured observations through 2026-07-28;
- MCX bhavcopy: 144 structured EOD contracts dated 2026-07-29;
- NSDL FPI daily: 34 structured aggregate rows dated 2026-07-30;
- CFTC COT: 11 normalized commodity-market rows dated 2026-07-21;
- EIA weekly petroleum stocks: 19 structured metrics dated 2026-07-24;
- BSE buyback index: 76 metadata rows linked to 140 archived XBRL documents;
- BSE takeover index: 158 metadata rows linked to 267 archived XBRL documents.

All 407 linked BSE documents were downloaded and parsed. The BSE contract was
hardened so zero price/quantity POST documents remain archived but cannot
become structured offer evidence. An all-skipped refresh now reports
`STRUCTURED_OK` instead of a false wait. Point-in-time ISIN mapping connects
current positive-term offers to NSE symbols only when the latest eligible NSE
instrument identity is active. Observed current usable mappings: 67 buyback
symbols and 31 takeover symbols.

Focused BSE tests: **8 passed**. Complete backend: **541 passed**. Frontend:
**135/135 passed**. Offer evidence remains a contextual CAUSE/event-price
anchor; it cannot independently authorize `CONFIRMED` or imply tender
acceptance, fillability or guaranteed return.

## 2026-07-30 - Old-versus-pasted source download comparison

Twelve supplied source purposes were executed through both the existing
TrendForge implementation and the newly pasted prototypes where available.
Success required populated, parsed market or economic records; HTTP status,
metadata-only responses and parser invocation did not count.

- Existing canonical paths produced populated data for **12/12** source
  purposes.
- Pasted paths produced populated data for **10/12**; the pasted ASM route was
  a wrong `404` endpoint and the pasted NSDL parser did not match the current
  page layout.
- The pasted MCX parser materially improved retained research data: **16,435**
  schema-valid futures/options contract rows across 30 symbols, of which
  **1,112** had positive volume or OI. The existing parser retained 144 rows.
- The pasted CFTC path retained **7,847** historical rows; the canonical parser
  retained the latest 11 normalized commodity-market rows with PIT storage.
- NSE all-indices results were equivalent. Canonical F&O pre-open currently returned 208 normalized symbols; the pasted NIFTY pre-open route returned the narrower 50-stock set. The canonical ASM and
  NSDL implementations remain the working choices. Bhavcopy, BSE offer, CFTC,
  EIA and MCX research archives benefit from a hybrid retention strategy.

All outputs were retained under
`data/raw_sources/verified_downloads/2026-07-30/`. The canonical comparison
files are `OLD_VS_NEW_USABLE_DATA_COMPARISON.csv` and
`OLD_VS_NEW_USABLE_DATA_COMPARISON.json`. The archive contains 444 files,
including all 407 linked BSE XBRL documents. These downloads are research
artifacts for later scanner integration; they do not activate sources or
authorize `CONFIRMED`.

## 2026-08-01 - Single-spine residual governance re-verification

Residual governance nits were re-verified as closed: the pick-next-M trap
rejects action-shaped M/T/PK selection while allowing safe negation; the
work-packet selector accepts only File A `R0-R18`, `CROSS-###` or
`TDG-GAP-###`; and `FMR-011` remains split across the R15 presentation shell,
R16 deterministic replay/PIT dataset and R18 promotion/rollback governance.

Governance verification: **26 passed**; coverage check: **155 rows with zero
drift**. Runtime manifest hash:
`07E2F9E7C107CF480D1A98CE4AF9B30547B1BA23580DF7123C971A98360D85BB`.
This was governance-only verification; no runtime product behavior changed.
## 2026-08-01 - Plan crosswalk and score-law lock (docs only)

Appended mandatory plan hygiene without runtime product change:

- File A section 9.3: File A SEL S0-S9 vs FMR-002 story S0-S9 vs Hybrid Stages crosswalk; ban third S-map
- File A section 9.4: single public-state owner (resolver + profile gates); API/UI project only
- File A section 9.5: forbidden Combined_Score / win-percent product authority
- File A section 9.6: minimum property-test teeth list
- File A section 11.2: evidence_strength is not Combined_Score; state only after section 10.4
- FINAL_MERGE FMR-002: story labels mapped to File A; no Combined_Score product
- remaining_build README: R0 residual checklist + S-number discipline
- Discovery Detail Plan: Modes A-E, G1-G8 vs G00-G14, E1/E2 catalog lock
- Options Detail Plan: File A S-number pointer for deep options path

This is documentation only. No activation, CONFIRMED unlock, qty, OMS, or scanner business-logic change.

Also restored empty root \ileindex.md\ (was 0 bytes) as navigation-only index with math mapping tokens; governance suite 26 passed; coverage 155 zero drift.

## 2026-08-02 - Options Best Research Playbook merged (docs only)

Merged filtered operational playbook into docs/OPTIONS_INTELLIGENCE_PLAN.md as section 18:

- Correct-use matrix (Greeks, PCR, max pain, GEX, VRP, hero-zero, settlement, MWPL)
- Options-aware stock selection tree + structure x package fusion matrix (no Combined_Score)
- Strike goals with RESEARCH_DEFAULT_v0.1 bands; lottery OTM not master-rank
- Entry/exit research geometry qty=0; banned UI strings
- Expiry-day honesty + hero-zero RESEARCH_ONLY
- Output contract with File A four states only
- R-order implementation table R0..R18 path
- Package-internal P-steps labeled narrative; File A SEL remains build authority

Sources: File A + FMR + Options plan + Kimi section review filtered (rejected invented public states and third S-maps).
No runtime/activation/CONFIRMED/qty change.

## 2026-08-02 - Options playbook hybrid truth-behind-maths (docs only)

Updated existing docs/OPTIONS_INTELLIGENCE_PLAN.md section 18 (v1.3) â€” no new file:

- 18.0A truth behind maths (Greeks/OI/IV/max pain/score what is hidden)
- 18.0B false-confidence attack table
- 18.0C residual locks (cash-gamma worship, mid-solve spread gate, independent family, WAIT default)
- Claim classes FACT|MODEL|SCENARIO|LOTTERY|UNKNOWN
- Self-test checklist 18.10; hybrid creed 18.11
- Merged Kimi design-audit truths + Grok enforcement with File A law

No runtime/activation/code change.

## 2026-08-02 - Options Â§18 GPT MINOR fixes applied (docs only)

Applied verified GPT PASS_WITH_FIXES items to docs/OPTIONS_INTELLIGENCE_PLAN.md v1.4:

1. Hysteresis demoted to uncalibrated preference (not File A product rule)
2. S6-S7 cited as SEL-007/008; File A Â§10.4 = prerequisites checklist only
3. qty=0 for ordinary rows; VRP research lot exception pointer to File A Â§25.23
4. Â§4 package narrative: structure S4 before options package S5
5. sourceActivationReady=false ceiling and evidence_strength UI label stated

Did not treat File A Â§25.25.6 as non-S map; noted it as narrative to crosswalk to Â§9.
No runtime/code change.

## 2026-08-04 - Guarded live-panel snapshot (activation pending)

Implemented M1-M3 of `docs/fable/LIVE_PANELS_PLAN_2026-08-04.md`: ten P0 live adapters, shared `trendforge.livePanels.v1` snapshot, exact panel freshness gates, session scheduler, kill switch, breakers, localhost API, and immutable inventory-app overlay. Consensus v4 and Screener v1.3 formulas were not changed.

Status: **verified with caveats; activation pending**. An isolated pinned `.venv` is installed; focused backend tests are 10/10, changed-file Ruff/mypy pass, and a bounded real-network smoke populated all ten sources. No real database projection migration or service activation was performed. See `docs/fable/LIVE_PANELS_IMPLEMENTATION_REVIEW_2026-08-04.md`.

## 2026-08-06 - MD69 parameter-resolution repair

Repaired the existing manual/scheduled collection path for BSE announcements,
NSE shareholding, PIT, sector constituents and equity option chains. Base feeds
now commit first; a bounded saved-data context then supplies only dependent
feeds. Existing failure isolation, rate limits and last-good behavior remain.
No scoring or broker behavior changed.

Observed full refresh: **69 attempted / 69 completed**; 60 populated
successes, 2 valid-empty, 6 failed and 1 partial. All five repaired contracts
behaved as intended. See
`docs/fable/MD69_PARAMETER_RESOLUTION_REVIEW_2026-08-06.md`.

## 2026-08-10 - Pack-2 shipping and search-context sources completed

Completed the existing partial implementation for three independently useful
context feeds without adding a downloader, database, or score path:

- `tradingeconomics_bdi`: third-party Baltic Dry Index context.
- `yahoo_bdry_shipping_proxy`: BDRY ETF proxy, explicitly not BDI.
- `google_trends_india_rss`: official current India trend topics, not keyword history.

All three now have resolver branches, structured parsers, source-monitor
descriptors, last-good retention, freshness/storage metadata, scheduler
contracts, CSV/YAML profiles, and hash pins. The dynamic collector registry is
now **104/104**, with provisional schedules still `activation_ready=false`.
Consensus and Screener formulas, catalog cards, and panel voting roles were not
changed.

Observed canonical objects dated 2026-08-10: BDI **1**, BDRY **251**, Google RSS
**10** normalized records. The full backend suite is **673 passed / 10 unrelated
failures**; the remaining failures predate and do not reference these three
source keys.

Focused production re-verification on 2026-08-10 kept all three populated and
updated the BDI parser contract to **1.1.0**. The current BDI object has value
**3,083**, previous value **3,089**, absolute change **-6**, and daily change
**-0.19%**. This is third-party market-regime context only; it does not vote or
change Screener/Consensus scores.

## Pack-3 rating sources - CRISIL and ICRA (2026-08-10)

`crisil_ratings` and `icra_ratings` are now complete production collector
contracts. The registry is **106/106** and remains provisional/disabled for
automatic activation. Live proof: CRISIL archived and normalized 100/100 rows
dated 2026-08-10 (attempt 1512); ICRA archived and normalized 20 rows dated
2026-08-10 (attempt 1515). Both preserve company identity without fuzzy ticker
mapping and are `ZERO_SCORE_INFORMATIONAL` only. The Inventory catalog now has
148 rows / 112 logical keys, with populated cards for both sources.

CARE was added next through the same production path. The current registry is
**107/107**. Live CARE proof stores 1,000 rows dated 2026-08-10 (attempt 1516),
with a 250-row catalog sample. The catalog is now 149 rows / 113 logical keys.

Google News RSS completes Pack 3 through the same path. The registry is now
**108/108** and the catalog is **150 rows / 114 logical keys**. Live snapshot
492 archived a 562,285-byte five-query bundle; 234 source items were checked and
4 articles inside the seven-day age window were normalized through attempt 1517
(`SUCCESS_NEW`, data date 2026-08-09). The source is aggregated publisher
context only, unmapped and zero-score. Pack 3 final classifications are recorded
in `docs/fable/ADD_40_SCREENER_LINKS_PLAN.md`; Pack 4 is next.

Pack 4 has started with an enhancement of the existing `usda_wasde_cornell`
key. It now discovers release 795974 through official ESMIS, parses the full
official XML and retains Cornell only as fallback. Snapshot 493 archived
2,112,908 bytes; parser v2.0.0 preserved 5,414 populated attribute values and
attempt 1518 stored them as `SUCCESS_NEW` dated 2026-07-10. Registry remains
108 keys with updated contract SHA `B1EB1A7F...`; catalog row 124 now shows the
official source and 250/5,414 sample/usable rows. TrueData is BLOCKED by licensed
credentials.

Angel's public master is now added as key 109. Snapshot 494 archived all
152,044 source rows (35.6 MB). The accepted product scope compacts 112,223
NSE/BSE/NFO/BFO/MCX contracts into 24,063 reference schedules; current attempt
1520 is 28.7 MB and `SUCCESS_NEW`, dated 2026-08-10. The first 247-MB
per-contract object was rejected as inefficient and superseded, not deleted.
Catalog is 151 rows / 115 logical keys with a 250-row Angel sample. It is
catalog/reference-only and zero-score. Dhan's public master is next.

Dhan's public detailed master is now key 110. Snapshot 495 archived 205,781
CSV rows (34.9 MB). A live identity audit found that security IDs repeat across
segments, so the accepted key is exchange + segment + security ID. Attempt 1522
stores 24,283 schedules representing 155,175 in-scope rows in 35.1 MB, dated
2026-08-10. Catalog is 152 rows / 116 logical keys. The source is reference-only
and zero-score; authenticated Dhan charts remain blocked.

## 2026-08-11 â€” Dead source routes quarantined

Five verified dead/unusable routes are retained only as `NOT_IN_USE` hints:
Yahoo `^BADI`, `pytrends`, StockEdge "API", BSE `FIIDII/w`, and BSE
`ParticipantWiseOI/w`. The two old BSE functions in the incoming prototype are
non-network stubs and are no longer called by its main path. Working replacement
contracts remain active. Observed counts did not change: 119/119 typed registry
keys and 161 catalog rows / 125 active logical keys. No scoring file changed.

## 2026-08-11 â€” FII-related stock-name evidence API

`GET /api/institutional/fii-stock-signals` now reads only the latest saved
`SourceParseResult` objects for the approved NSE/BSE bulk, block and
shareholding keys. It emits large-deal stock anchors with an explicit warning
that named clients are not certified FII, plus quarterly FII/FPI holding
changes only when an explicit percentage delta (or current + previous values)
exists. Market-wide FII/DII totals are never used for stock names.

Observed saved-data smoke: HTTP 200, 106 large-deal rows, 33 unique symbols,
and 0 quarterly FII/FPI changes. The zero is expected because current saved
shareholding rows do not contain qualifying change fields. Inventory SPA now
shows these names in a separate informational strip directly below the Nifty
Filter; `consensus.js` and screener scoring are unchanged.

## 2026-08-02 - Inventory integration plan corrected (docs only)

Updated docs/fable/INVENTORY_WORKBENCH_INTEGRATION_HANDOFF.md:

- Trading-architecture reasoning first (attention vs confirmation)
- Live counts (165 cards / 129 unique active_source_keys / 123 registry / 105 unique primary rows) â€” do not freeze filename 105
- File A sole sequence; R0 then R1 then R2 (M-tags are seams)
- CROSS-002 not repeated; real R0 residuals listed
- Frozen inventory + VM-shim v1.3 screener; bundle from TF PIT not samples
- New decision UI on TrendForge frontend; no dist/ assumed; no second live-panel
- remaining_build README Step B pointer aligned

Inventory app not edited. No runtime change.

## 2026-08-14 - Inventory handoff count and adapter ownership corrections

Corrected docs/fable/INVENTORY_WORKBENCH_INTEGRATION_HANDOFF.md and the prior
2026-08-02 status bullet:

- Observed counts: 165 cards; 129 unique active_source_keys (pipe-split);
  123 collector contracts; 105 unique primary rows
- Updated date 2026-08-14; supersedes the 2026-08-04 M0-M5 narrative (no
  impossible 02-replaces-04 sequence)
- Adapter is not a fifth milestone: hash-pin R0; PIT bundle R1/CROSS-019/
  TDG-GAP-004; ranks/shadow R2/CROSS-004/TDG-GAP-014
- Options Â§18 activation line now uses observed-runtime wording for the
  governance validator

Inventory app not edited. No runtime/product change.


## 2026-08-15 - Embedded Source Operations panel

- The Inventory button loads the bundled workbench at
  `/inventory-workbench/?embed=terminal&v=20260815-source-operations` inside the
  existing terminal drawer. The separate inventory page remains available.
- The Source Operations panel sits below the five KPI cards and reads the
  compiler report, source monitor catalog, fetch attempts, parser outputs and
  freshness status. It shows six stages from registered contracts to facts
  usable for research, plus per-source state and failure reason.
- States are `HEALTHY`, `VALID_EMPTY`, `STALE_PARTIAL`, `BLOCKED`, `FAILED` and
  `NOT_ATTEMPTED`. It does not infer health from catalog samples, does not claim
  automatic retries, and cannot rank, activate, emit `CONFIRMED`, calculate
  quantity, or execute orders.
- Embedded mode uses only the scoped `inventory-embedded` class. Source and
  bundled runtime assets remain synchronized; the inventory manifest remains
  the snapshot boundary.
- Browser observation: the drawer loaded the panel directly below the KPI
  cards and the stale filter displayed 50 source rows. The run observed
  `354/132/56/47/5/5` through the six stages and status counts
  `5/1/50/0/0/76`. These are timestamped operational observations, not permanent
  counts.
- Focused syntax and browser checks passed for the changed JavaScript and panel.
  Existing unrelated warnings remain: refresh/status 503, selection/live 404
  and favicon 404.


## Hash-pin caveat - 2026-08-15

The source and bundled runtime files contain aligned feature markers but are separate revisions and are not byte-identical for this
change, but the existing snapshot manifest still contains the pre-Source-
Operations byte sizes and hashes. The existing `inventory-workbench.test.js`
also still expects the old drawer URL without `embed=terminal`. Its current
observed result is **FAIL: Size mismatch: index.html**. This means the runtime
panel observation is valid, but the manifest/test pin must be refreshed before
claiming a clean snapshot-integrity verdict. No source data, catalog sample, or
TrendForge state authority is affected by this metadata/test discrepancy.

## 2026-08-15 - Refresh/Scheduler post-commit bridge and Source Operations

The existing A1-C1 cash research stages are now connected to the saved-data boundary through selection/cash_post_commit.py. MarketDataScheduler dispatches the bridge only after a collector run has persisted a schema-valid manifest and last-good result. Manual snapshot, EOD and registry refresh paths use the same dispatch hook. The frontend does not run A1-C1.

Only cash-relevant changes can start the cash path. Repeated relevant fingerprints are idempotent. Unrelated source changes are skipped. A downstream research failure records FAILED_STAGE without rolling back a successful collector save. C0 permissions are reused unless compiler/contracts change. B remains MWPL_MISSING unless a proven official percentage artifact exists.

GET /api/source-operations/snapshot is the single read model for the embedded Inventory Workbench. Its source-flow track shows compiler, runtime, attempt, parser, freshness and last-good evidence. Its cash track shows A1, A2, A3, A4, A5, A6, C0, B and C1 states. Activation, CONFIRMED, quantity and broker actions remain disabled.

Verification: focused backend bridge/API/scheduler suite 38 passed, 1 warning; source and bundled JavaScript syntax checks passed; full backend baseline 851 passed, 21 failed; inventory frontend suite 13 passed, 2 failed; bundled integrity test failed on the pre-change index.html manifest size. Feature wiring is present, but manifest/test-pin and unrelated regression contracts still need separate reconciliation.

## 2026-08-15 - Refresh downloads registry jobs, not 165 cards

Inventory Refresh is `POST /api/market-data/refresh` on this API. The inventory SPA never fetches market sites. 165 catalog cards collapse to 129 unique keys; Refresh runs the 123 hash-pinned registry contracts. Six catalog-only names (`nse_block_deal_live`, `nse_live_equity_derivatives`, `nse_market_variations`, `nse_option_chain`, `nse_pit_current`, `wgc_gold_etf_flows`) are normalized aliases of those jobs, not missing downloads. Companion/provenance cards are not extra fetches.

A server started without `MARKET_DATA_69_ENABLED=1` and `MARKET_DATA_69_PROVISIONAL_OVERRIDE=1` returned HTTP 503 on Refresh. `run_server.py` now defaults both flags on for local API start. Source Operations last-good matching resolves the same aliases so a family card is not shown as missing when its parent job is already stored. HTTP 200 / junk HTML / empty / stale is still not usable.

## 2026-08-16 - Handoff and MD69 reference aligned to live pin

`docs/fable/MD69_REFRESH_OPERATION_REFERENCE.md` Â§1 records 123 jobs, 165 catalog cards, 129 unique catalog keys and 122 current display-collapse groups. `links_105.json` is a legacy filename; 105 is historical inventory baseline, not a current collector count. The reference also records six aliases, default collector flags, the single snapshot API and the latest full-registry manifest. `docs/fable/INVENTORY_WORKBENCH_INTEGRATION_HANDOFF.md` now treats Source Operations as `GET /api/source-operations/snapshot`, marks A1â€“C1 as already wired, and declares overlay re-pin instead of a frozen byte-identical source app. `frontend/tests/inventory-workbench.test.js` accepts `embed=terminal` and overlay-listed glass files; scoring engines must still match the frozen source. Integrity test: 24 copied files verified.

## 2026-08-16 - R1/R2 remaining tickets; workbench not connected

File A **R1** remaining = live evidence DTO (123 jobs, 6 aliases, cadence clocks, why-not-confirmed, PIT bundle). File A **R2** remaining = attention order over existing A1â€“C1 plus inventory shadow queue. Neither ticket rebuilds cash A1â€“C1. Neither ticket is shown on `/inventory-workbench/?embed=terminal`. Source Operations last-good / HEALTHY counts are collector health, not stock rank. Connecting R1/R2 objects to that page is a later display ticket only. Plan: `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` Â§Â§9â€“11. Decision: `docs/DECISIONS.md` D-034.

## Historical R3 pre-build checkpoint - 2026-08-16 (superseded)

**Historical snapshot only.** This was accurate before the later R3 implementation record at `2026-08-16 - R3 live evidence-family resolution` and the 2026-08-17 documentation reconciliation.

R1/R2 were live. File A R3 was specified but had not started. The locked how-to remains `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` **Â§13**: adapter from R1 â†’ existing `resolve_evidence`, WAIT ceiling, attach selected/suppressed claims, do not change R2 order or write CONFIRMED, do not use the workbench. Do not re-plan R3 at build time.
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

### Current implementation verdict

- Manual Refresh is operational and attempts 123 registry contracts.
- The calendar-aware repair is verified: post-commit derives the expected latest NSE EOD date from the official calendar. A weekend Refresh therefore uses the prior valid session date rather than its wall-clock collection date; unknown calendar state blocks the path as `BLOCKED_INPUT`.
- Standard local API startup now sets `MARKET_DATA_69_AUTOSTART=1` and FastAPI starts one guarded 15-second `MarketDataScheduler.start_foreground()` task. Direct bare Uvicorn startup must set the same environment flags explicitly. Windows logon persistence is not claimed.
- The bundled integrity test currently fails at `Size mismatch: index.html`; six of 24 manifest files differ from the source app.
- No source activation, CONFIRMED path, quantity or broker authority changed.

## 2026-08-16 - BSE filing-index recovery and MCX fail-closed transport repair

The existing collector was repaired; no second download plane was added. BSE bare `{}` session responses trigger the official page and default-window warm sequence. Live verification showed that BSE still returned `{}` to `httpx` on this host while the same official sequence returned populated `Table` data through Python's standard-library browser session. `AsyncEndpointClient` therefore uses a bounded, source-specific stdlib fallback only after a bare BSE response; it fully consumes seed/warm responses, then returns the target body to the existing parser, archive, store and last-good path. Live collector runs committed `bse_financial_results_xbrl` with **9,706 source rows / 9,036 normalized rows** and `bse_shareholding_pattern` with **5,530 normalized rows**, both dated **2026-08-15**.

`mcx_bhavcopy` now uses the current official `/market-data/bhavcopy` route with Chrome-compatible TLS transport and accepts a response only when the populated embedded bhavcopy payload is present. On 2026-08-16 the official host redirected every checked route to its Sitefinity status page, so the collector failed closed and retained the last-good **145** rows dated **2026-08-13**. It did not archive the status page as market data.

Registry identity remains 123 contracts. The URL repair changed the registry SHA-256 to `16197B10B7A8DA9A7DB475FF59BA2DDA325219354438A8280CB1CF9AEE8AB070`; CSV, `.sha256`, YAML profile pin and compiler pin match. Current BSE verification: **10 focused tests passed**, **53 service/scheduler tests passed**, targeted Python compilation passed, and frontend checks passed **161/161**. The complete backend suite observed **857 passed / 21 failed**; all 21 failures are outside the two BSE files and remain existing project baseline debt, so this repair does not claim a globally green backend.



## Refresh, automatic scheduler and A1-C1 live verification - 2026-08-16

**Purpose.** One collector remains responsible for acquisition. The browser is only a local control surface; it does not fetch exchange sites or decide a trade.

| Connection | Implemented code and function |
|---|---|
| Manual Refresh | `POST /api/market-data/refresh` -> `ManualRefreshCoordinator.start()` -> one `MarketDataScheduler.run_all()` run over 123 registry contracts. |
| Automatic cadence | `backend/run_server.py` and `scripts/start_api_md69.ps1` set `MARKET_DATA_69_AUTOSTART=1`; `main.py` FastAPI lifespan starts exactly one `start_foreground(poll_seconds=15)` worker. It evaluates 09:00, 09:17, 10:30, 12:30, 13:30 and 15:00 IST plus EOD. |
| Acquisition to storage | Scheduler -> `MarketDataService` -> persistent endpoint client/resolver -> strict parser -> raw archive, normalized object, manifest and content-addressed last-good pointer. A transport success is not data success. |
| A1-C1 handoff | `MarketDataScheduler._dispatch_post_commit()` calls `expected_latest_nse_eod_date(at)`. Calendar-unknown blocks. Cash-relevant, structured, current saved data only then enters `CashPostCommitOrchestrator`; unrelated keys skip and equal fingerprints reuse/skip. |
| Workbench visibility | `GET /api/source-operations/snapshot` projects source lineage and cash-stage state into the read-only inventory drawer. It cannot activate a source, authorize `CONFIRMED`, calculate quantity, or create an order. |

**Observed full run.** `2026-08-16-manual-20260816-160551-9e7a3429071a` completed: 123 attempted, 119 `SUCCESS_NEW`, 1 `STALE_LAST_GOOD`, 3 `VALID_EMPTY`, 0 failed. Its post-commit run used official EOD `2026-08-14`: A1 2,463 cash facts, A2 2,463 identity/restriction facts, A3 1,723 WATCH rows, A4 2,463 immutable bars, A5 skipped because current index context was unavailable, A6 completed for the WATCH shortlist, C0 reused, B skipped with `MWPL_MISSING`, and C1 completed 2,463 research rows. The public ceiling remains `WATCH_WAIT_REJECT`; `sourceActivationReady=false`, `canUnlockConfirmed=false`, and `executable=false`.

**Verification.** Focused scheduler/post-commit/API tests: 38 passed. Full backend: 861 passed, 21 pre-existing unrelated failures. Frontend: 161/161 passed. Workbench integrity: 24 copied files verified.

## 2026-08-16 - R1/R2 regression closure and globally green suites

This entry supersedes the earlier same-day statements that R1/R2 were still
pending or that the backend retained 21 unrelated failures.

**Implementation.** The remaining regression debt was reconciled against
current contracts rather than hidden by weaker assertions:

- IV rank again requires an explicit official trading-session set, rejects
  invalid/weekend/mixed-underlying observations, uses exactly the latest 252
  distinct valid sessions, and remains informational/non-scoring.
- Upstox PCR parsing now whitelists provider fields and cannot override
  sourceTrust or scoreEligible; invalid OHLC geometry is quarantined; and
  corporate-action names and dated details follow the observed provider schema.
- Resolver HTTP injection now resolves the current fetch_url function at call
  time, so bounded test/recovery transports are honored.
- CROSS-002 source-map review was re-pinned as
  CROSS-002-2026-08-16-v2 to the already expanded, observed map:
  157 named inventory keys, 132 runtime catalog keys and 176 union keys.
  Review completion does not grant activation: gate-authorized keys remain 0.
- Stale tests were aligned to intentional current contracts: 24 migrations,
  120-second BSE pledge timeout, three-page NSE warm-up, ISO option expiry,
  reviewed F&O-ban archive candidates, 32 reviewed overlaps, third-party LME
  fallback semantics and async tests that do not require an uninstalled plugin.

**Observed verification.**

- Focused repaired areas: **107 passed**.
- Complete backend: **897 passed, 0 failed, 1 deprecation warning**.
- Complete frontend: **161/161 passed**.
- Bundled Inventory Workbench integrity: **24 copied files verified**.
- Local API restarted on 127.0.0.1:8000 as PID 25192; root returned HTTP 200.
- Compiler API: review valid, 176 reviewed keys, 0 gate-authorized,
  sourceActivationReady=false.
- R1 API: schema trendforge.inventory-source-bundle.v1, 123 source records,
  2,463 stock records, ceiling WATCH_WAIT_REJECT, 0 gate-authorized.
- R2 API: schema trendforge.inventory-discovery.v1, BASELINE mode,
  2,463 rows = 1,720 WATCH + 743 WAIT + 0 REJECT, 0 CONFIRMED and 0 populated
  entry/target/stop geometry. Shadow output cannot vote or change baseline.

**Remaining caveat.** The only complete-suite warning is Starlette's deprecated
TestClient/httpx compatibility layer. It does not fail current behavior, but its
dependency migration remains future maintenance. Globally green tests do not
make source activation true and do not prove production market-data freshness.
## 2026-08-16 - R1/R2 source-specific freshness closure

Status: **VERIFIED. R3 is next and was not started.**

R1 now evaluates every one of the 123 registry jobs against that source's
existing cadence, publication, active-window, holiday/closed-day and empty-data
rules. The additive `registry-cadence-v1` contract records the expected trading
date, freshness state/reason and age in the existing source clock. Populated
stale, future or temporally unknown rows remain inspectable but are not evidence
eligible. R2 maps those rows to WAIT with no attention rank; it still emits no
CONFIRMED state and no entry/target/stop geometry.

The post-commit fingerprint now includes the freshness-policy version, so a
policy change rebuilds R1/R2 exactly once instead of being skipped by an older
completed-run fingerprint.

Observed manual refresh `2026-08-16-manual-20260816-201419-773f37c58f0e`
attempted all 123 jobs: 119 completed with new data, 1 retained stale last-good,
3 were valid-empty and 0 failed. R1 produced 123 source records and 2,463 stock
rows: freshness 94 CURRENT, 11 STALE and 18 UNKNOWN; usability 91
USABLE_CURRENT, 3 VALID_EMPTY_CURRENT, 28 STALE_DATA and 1 STALE_LAST_GOOD. R2
produced 1,720 WATCH and 743 WAIT rows, with 0 ranked non-current rows, 0
CONFIRMED and 0 trade geometry.

Verification: 29 focused tests passed; the complete backend passed **905**
tests with one existing Starlette/httpx deprecation warning; the complete
frontend passed **161/161** checks. Registry cadence authority remains
provisional and source activation remains false, so CURRENT means current under
the reviewed internal source contract, not trade or confirmation authority.

## Historical R3 pre-build audit - 2026-08-16 (superseded)

**Historical audit only.** Later R3 implementation supersedes its live-not-started conclusion; its gap analysis remains retained as design evidence.

- R3 live remains NOT STARTED. Existing resolve_evidence usage and Q5-R3 CONFIRMED behavior are fixture-only.
- No live claim adapter, resolution builder/store helper, or GET /api/v1/selection/resolution route exists.
- The public R1 DTO cannot reconstruct exact SourceResult and NormalizedFact PIT lineage; R3 must consume the in-memory A1/A2 objects at the cash post-commit boundary.
- Current compiler observation: zero source contracts expose feature IDs or directional permission. nse_bhavcopy_eod is UNSPECIFIED_NO_VOTE.
- Therefore selected live claims are blocked pending the separately approved authority contract described in locked plan section 13.9. Diagnostic suppressed/no-claim plumbing alone cannot complete R3.
- R2 bytes, state and order remain immutable. Live R3 retains WAIT ceiling, activation false, and no trade geometry, quantity, probability or broker fields.
## 2026-08-16 - R3 live evidence-family resolution

Status: **IMPLEMENTED AND VERIFIED at the research-only WAIT ceiling.**

- Added canonical `FTR-040` for closed NSE EOD cash participation. The compiler grants only `nse_bhavcopy_eod` the `PARTICIPATION` family, `CG_ACTIVITY_SESSION`, `SWING`/`NSE_EQ`, and `RESEARCH_DIRECTIONAL_WAIT_ONLY`. All other compiled roots remain non-directional; gate-authorized source count remains zero.
- Added `selection/r3_claim_adapter.py` and `selection/r3_live.py`. Claims require exact A1 `SourceResult`, A2 `NormalizedFact`, R1/R2 hashes, current compiler permission fingerprint, exact factId/date/artifact lineage and R1 cadence qualification. Generic source cards, aliases and companions cannot create stock claims.
- Extended cash post-commit to R3 without rolling back collector/R1/R2 on R3 failure. Duplicate inputs recover a missing R3 from immutable stored R1/R2 without rerunning them.
- Added read-only `GET /api/v1/selection/resolution`. GET never computes. It returns 503 for missing or hash-mismatched R1/R2/R3.
- Runtime replay from the saved populated NSE EOD artifact completed A1-R3: 2,463 R3 rows, all WAIT; 2,437 selected participation claims, 0 conflicts, 0 CONFIRMED, 0 entry/target/stop/quantity fields. `sourceActivationReady=false` and `canUnlockConfirmed=false`.
- Before local replay, the previous R1 permission fingerprint differed from FTR-040 and the API correctly returned 503. Rebuilding R1/R2 under the new fingerprint produced a hash-matched persisted R3 and API HTTP 200.

Verification: focused R3 suite 67 passed; complete backend 909 passed with one existing Starlette/httpx deprecation warning; frontend 161/161 passed. R3 does not activate intraday, MCX, options or event claims. Those require later reviewed source-feature contracts in File A order.

## 2026-08-17 - R1/R2/R3 architecture and graph reconciliation

The short executable architecture map and interactive system data-flow map now
match the implemented saved-data selection path. `docs/ARCHITECTURE.md` records
R1 evidence qualification, R2 BASELINE attention and R3 WAIT-only FUS-009
resolution as implemented at their scoped research ceilings. It names the three
read-only APIs and keeps the Inventory Workbench outside selection authority.

`docs/interactive_system_data_flow_map.html` now shows saved cash facts -> R1
-> R2 -> R3, distinguishes those live artifacts from Q5 fixtures and legacy
selection display, and records FTR-040 as the sole directional contract. The
remaining build README and locked R0/R1/R2 plan contain the same checkpoint and
a hash/lineage-first debugging handoff. The root architecture and source
registry already carried the corresponding R3 record.

No runtime code, collector behavior, source activation, scoring, UI binding or
trade authority changed. Next code milestone remains R4.
## 2026-08-18 - Official NSE cash history backfill for R5 structure tags

1. Added `scripts/backfill_nse_cash_eod.py` (CLI: `--days` default 10, max 15, `--through`). It downloads dated official `BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip` URLs, parses with the existing cash parser (EQ only), and persists via the existing immutable A4 `_store_raw_bar` (INSERT OR IGNORE; hash conflicts refused).
2. It never writes `market_data_latest`, never touches the 2026-08-18 last-good anchor, never refreshes the other 122 sources, and uses no Yahoo/broker/paid APIs. Verified: A1 staging and `market_data_latest.nse_bhavcopy_eod` still show 2026-08-18.
3. One fix during bring-up: the resolver also lists `PRddmmyy.zip` bundles; those parse as `WAIT_EMPTY_PARSE`, so the script now tries the `BhavCopy_NSE_CM_` URL first.
4. Backfilled 20 trading days (2026-07-17 .. 2026-08-17) in idempotent chunks: 21 session-days saved, 0 missing, 0 failed, 0 hash conflicts; ~51,900 new raw bars.
5. Rebuilt ONLY R5 (`build_r5_structure_batch` + `persist_r5_structure_batch`) against the unchanged R1/R2 fingerprints. R4/R5 engines unchanged; no FTR-040, no activation, no entry/stop prices.
6. Result: RELIANCE and TATASTEEL now have 21 official session bars; `WAIT_INSUFFICIENT_HISTORY` dropped 2,598 -> 307 rows; 904 rows carry research tags (NR7 454, RVOL 348, CLOSED_BAR_BREAKOUT 211).
7. R5 stays `LIVE_WAIT_REJECT_ONLY`: all 2,632 rows WAIT (`R5_LIVE_WAIT_CEILING` + `WAIT_INDEX_CONTEXT_MISSING`); CONFIRMED = 0 persisted and via API.
8. `GET /api/v1/selection/structure` returns HTTP 200, tradingDate 2026-08-18, universe 2,632, waitCount 2,632, rejectCount 0, confirmed 0.
9. Structure tags are deterministic research evidence only; the index context file still does not exist, so the live ceiling remains WAIT by design.
10. Remaining gaps: ~307 thin-history rows (new/listed-late symbols) and 232 `NR_HISTORY_INCOMPLETE`; both need more official sessions, not new logic.

## 2026-08-19 - R5 live WAIT-only completed (CONFIRMED stays closed)

R5 live structure is **done at the File A research ceiling**. It is not
production CONFIRMED. A 2026-08-19 draft that claimed 836 live CONFIRMED
rows and `can_unlock_confirmed=true` contradicted D-035, locked plan Â§12.3
item 8, and R14 (CA join still missing). That unlock was reverted. Setup
tags (CLOSED_BAR_BREAKOUT / NR7 / RVOL) remain research stickers on WAIT
rows.

Completed in existing modules (no new voter, 123 jobs unchanged):

1. `GET /api/v1/selection/structure` is the live R5 read API. Ceiling
   `LIVE_WAIT_REJECT_ONLY`. `confirmedCount=0`. `canUnlockConfirmed=false`.
2. Official `nse_index_close_eod` is fetched as an A5 companion (not a 124th
   registry job). Missing class-average is `WAIT_INDEX_CONTEXT_MISSING`.
3. `MarketDataScheduler.reconcile_research_session` runs on startup and
   every poll without a Refresh click. NSE session clock is **Asia/Kolkata**:
   - PRE_OPEN / OPEN: last closed trading day
   - EOD_WINDOW (>= 15:35 IST on a trading day): today, only after the dated
     official file parses as today
   - CLOSED_NON_TRADING (holiday/weekend): last trading day, never relabelled
     as calendar today
4. Thin A4 history backfills official cash zips only, then R5 rebuilds.
5. SQLite leases/manifests still store UTC timestamps. Phase and research
   date are computed from IST.

Next code milestone after R4 live pin is **R14** (before any live CONFIRMED).
Qty/broker stay closed.

## 2026-08-19 - Live R4 identity pin (not A2, not A4, not CONFIRMED)

File A R4 live is implemented as `selection/r4_live.py` and
`GET /api/v1/selection/identity-pin`.

What R4 is: bind each R2 row to an existing A2 `instrument_id`; mark
`UNKNOWN_ID` or `COMPANION_REJECTED` explicitly; persist the PK0 inventory
digest with `pkUpstreamCanVote=false` and `pkRuntimeRequired=false`; apply
PIT/delisting only when membership fixtures are supplied.

What R4 is not: A2 identity, A4 bars/CA, Q5-R4 fixtures (`r4_fixtures.py`),
R7 PK worker, R5 structure, a 124th voter, or CONFIRMED.

Wiring: cash post-commit runs R4 after R3 and before R5. R5 still does not
consume R4. Frontend adapter loads identity-pin optionally (503 = null) and
does not paint R4 into rank.

Ceiling: `LIVE_ID_PIN_WAIT_ONLY`. Next before CONFIRMED remains R14 + R2-B.

## 2026-08-21 - Hybrid S4/S5 paper A/B overlay (not File A, not CONFIRMED)

Both original compressed S4/S5 and the split family stay until paper days
decide which to keep. Live compare is
`backend/trendforge_api/selection/s4s5_compare.py` and
`GET /api/v1/selection/s4s5-compare` (route in
`backend/trendforge_api/main.py`). Frontend panel is
`frontend/index.html` `#s4s5ComparePanel` plus new
`frontend/s4s5-compare.js`. Tests:
`backend/tests/test_s4s5_compare.py`. Checkboxes are WITH original S4/S5,
WITHOUT split, and BOTH. Default is BOTH.

WITH: `pÌ‚ = Ïƒ(-0.4 + 1.2Â·z_side + 1.2Â·z_book)`; entry = POCâˆ©WALLâˆ©PRZ (wall votes).
WITHOUT: `pÌ‚ = Ïƒ(-0.4 + 1.2Â·z_side)`; B4 = SUPPORT|WEAKEN|CONFLICT|UNKNOWN;
entry = structure box (wall = liquidity).

Calibration is `RESEARCH_PROXY_NOT_CALIBRATED`. Kelly shown is illustration,
capped 2%, not size. Rows stay WAIT. This overlay cannot rank, confirm, size,
or write into `r5_live.py`. File A next code milestone remains R14.


## 2026-08-21 - R14 live CA join completed WAIT-only (R5 consumes the join)

File A R14 is implemented at the `LIVE_CA_JOIN_WAIT_ONLY` ceiling. It is the
official corporate-action / identity-continuity join, not a 124th voter, not
live CONFIRMED, and not a rewrite of DAT-022.

New files (existing modules changed minimally):

1. `backend/trendforge_api/selection/r14_live.py` â€” `R14CaJoinRowV1` /
   `R14CaJoinBatchV1` / `build_r14_ca_join` / `persist_r14_ca_join` /
   `latest_r14_ca_join`. Validators forbid CONFIRMED, vote, rank, unlock and
   trade geometry; `WAIT_CA` rows cannot carry a factor version.
2. `backend/tests/test_r14_live_ca_join.py` â€” 22 tests covering T-013/096/096b/
   097/097b/098/099/113/178, PIT hiding, conflict, cancelled, identity break,
   UNKNOWN_ID / COMPANION_REJECTED, lineage fail-closed, ceiling validators,
   hash-scoped GET + POST 405, and R5 consume lineage.

Wiring (changed files):

1. `cash_post_commit.py` â€” pipeline is now `A1 A2 A3 A4 A5 A6 C0 B C1 R1 R2
   R3 R4 R14 R5`; `PIPELINE_VERSION` bumped to
   `a1-c1-r1-r2-r3-r4-r14-r5-orchestrator-7`; `CashPipelineExecution` /
   `CashPipelineRun` carry `r14_join_id`. If R14 fails, R5 is `BLOCKED` with
   `WAIT_R14_JOIN_NOT_READY` â€” no silent raw-vintage fallback.
2. `r5_live.py` â€” R5 requires a hash-matched R14 batch (R1/R2/R4 hashes);
   per-symbol CA authority is the R14 row (`NONE` / `ADJUSTED` / `WAIT_CA`
   with `WAIT_CA_CONFLICT` / `WAIT_CA_IDENTITY_BREAK` / `WAIT_CA_WAIT_DETAILS`
   gates); DAT-022 factors apply to pre-ex OHLC while volume divides only for
   SPLIT/BONUS; batch carries `r14RunId` / `r14RunHash`; `confirmedCount=0`.
3. `main.py` â€” `GET /api/v1/selection/ca-join` and `/{symbol}` are read-only
   and hash-scoped (mismatch â†’ 503 `R14_CA_JOIN_NOT_READY`; unknown symbol â†’
   404 `R14_SYMBOL_NOT_FOUND`; POST â†’ 405). `GET /structure` additionally
   requires the backing R14 join (503 `R5_R14_JOIN_NOT_READY`).
4. `market_data_scheduler.py` â€” the post-backfill R5 refresh now rebuilds R14
   first and skips quietly on `WAIT_*` (the GETs stay 503, never stale).

Semantics locked: future CA (`available_at > decision_at`) stays hidden and
counts in `hiddenFutureEventCount`; a newly visible CA changes `factor_version`
and therefore the adjusted series id (STO-020; RAW bars never mutate);
cross-symbol predecessor/successor without same-instrument proof is
`IDENTITY_BREAK`, not a ticker follow. `nse_corporate_filings_actions` remains
job `CA_SOURCE`; 123 jobs unchanged. S4/S5 overlay untouched.

Next code milestone after R14: R6 live enrichment. Live CONFIRMED still
requires R2-B and a separate File A amendment; qty/broker stay closed.

## 2026-08-22 â€” Hybrid V2 paper overlay (research package, not File A)

- New sibling package ackend/trendforge_api/hybrid_v2/ (contracts, spine_adapter,
  pipeline, persist, blocks B1-B5, stages S0-S9, as_lab, scorecard, tests_support).
- Two GET routes only: /api/v1/hybrid-v2/overlay and /api/v1/hybrid-v2/overlay/{symbol};
  POST 405; lineage mismatch/missing spine -> typed 503 (WAIT_HYBRID_*).
- Ceiling: RESEARCH_PROXY_NOT_CALIBRATED; canUnlockConfirmed/executable/sourceActivationReady
  all false. Phase-2 real work only: AS delivery z from official 
se_mto_delivery
  last-good (>=20 sessions at available_at <= decision_at), triple-barrier label spec
  (next-open fill only), cost-derived p_min / Kelly illustration (capped 2%).
- S4 reuses selection/s4s5_compare formulas exactly (WITH and WITHOUT kept);
  B4 stays a SUPPORT/WEAKEN/CONFLICT/UNKNOWN package; B5 labels only;
  S6 always UNKNOWN_NEEDS_R12. R1/R2/R14/R5 hashes are read-only (C14 verified).
- Frontend: same shell; added rontend/hybrid-v2-overlay.js, #hybridV2Chain
  inside section#flow (File A strip untouched), #hybridV2OverlayPanel under
  #s4s5ComparePanel; adapter also fetches overlay + ca-join (503 -> null).
- Tests: ackend/tests/hybrid_v2/ (42) + existing spine suites green;
  frontend acceptance-check 166/166.

## 2026-08-22 - R2-B named activation ledger (not CONFIRMED unlock)

Live R2-B is `selection/r2b_live.py` and `GET /api/v1/selection/named-activation`.
It names the R0-B official cohort and records that none may confirm.
`sourceActivationReady` stays false. `authorizedCount=0`.
This is not File A activation. Live CONFIRMED still needs a separate amendment.
Frontend `#r2bActivationPanel`. Tests: `test_r2b_live_named_activation.py`.



## 2026-08-23 - OI/Options rooms live (slices 1-8)

Package ackend/trendforge_api/options_intelligence/ (quadrant PRICE_*_OI_* + legacy alias, official MWPL BAN/RESUME/ALERT60 gate, Black-76 pricing+IV+greeks, chain quality, surface walls/pain/unsigned gamma, append-only IV + chain recorders, hard blocks incl. ban-add T+1 penalty / physical ITM T-2 / event-eve naked short / spread>8%, hero-zero+trend-time guidance JSON with prob_touch_P=null). Wired GET /api/v1/tools/{oi_analysis,oi_tracker,strike_explorer,expiry_prediction} (+405 on POST) in main.py. Frontend owner rontend/oi-options-live.js?v=20260823-oi1 (fixture delegates; no fixture fallback).

Tests: python -m pytest tests/test_options_pricing_suite.py tests/test_oi_analysis_bff.py tests/test_oi_tracker_bff.py tests/test_strike_expiry_bff.py -> 25 passed. Neighbors 	est_m_factor_bff.py test_api.py test_license_boundaries.py -> 87 passed.

Not yet live: real NSE lineage rows (BFF 503 WAIT_FO_LINEAGE until FO bhavcopy UDiFF artifact is persisted), chain snapshots for Strike/Expiry (WAIT_CHAIN until recorder receives one), P-probabilities and IV Rank (calibrate at R16).



## 2026-08-25 - R2-B CONFIRMED amendment executed + guidance OMS (ticket 4/4)

File A public CONFIRMED is now LIVE for PRF-003 NSE swing EOD via exactly five
named official sources (nse_bhavcopy_eod, nse_fno_ban, nse_fo_bhavcopy,
nse_index_close_eod companion, nse_corporate_filings_actions). The flip is
OBSERVED, never hardcoded: selection/r2b_live.py v2 authorizes the five only
when each has a current structured last-good (snapshot + PARSED_STRUCTURED +
fresh data_date); one missing/stale/broken last-good keeps
sourceActivationReady=false and lists blockers. MWPL can never authorize.

S7 (selection/s7_state_gates.py) seats CONFIRMED only when the observed ledger
is ready AND the full PRF-003 checklist passes; every fail-closed override
(ban, WAIT_CA, blackout unknown, weather unknown, conflict) still outranks it.
Regression kept: CONFIRMED forbidden while sourceActivationReady=false.
Batch now carries intradayGuidanceConfirmed (ON_FREE/OPENALGO lane, guidance
only) and per-row researchQuantity; CONFIRMED rows carry a guidanceOrderTicket.

New selection/guidance_oms.py: paper ticket (side/qty/entry/stop/notional/
remaining funds), OpenAlgo placeorder JSON preview with REDACTED api key, and
a triple-gated live path: TRENDFORGE_LIVE_ORDERS=1 AND effective lane
OPENALGO_RO AND UI arm switch on (default OFF). Default boot is preview only;
POST /api/v1/selection/guidance-oms/place returns 409 LIVE_ORDERS_ARMED_OFF.
Routes: GET /api/v1/selection/guidance-oms/{symbol},
POST .../preview, POST .../place, GET/POST /api/v1/settings/live-orders-arm.
s7_state_gates.py contains no order path (G3 NO_ORDERS).

Frontend: s7-state.js?v=20260825-s7-2 renders CONFIRMED chips, researchQty,
intraday badge; header chip flips to CONFIRMED EOD PRF-003 ONLY when ready
(still NO BROKER ORDERS). New guidance-oms.js panel (#guidanceOmsPanel,
#armLiveOrders default off, Preview ticket -> JSON preview, Place disabled
until armed). Tests: 36 amendment-suite tests, full backend suite 1245 passed,
frontend acceptance-check 212/212.

## 2026-08-25 - Full verification pass (all builds so far) + pit-gate route fix

Verification-only session after ticket 4/4. Full backend suite 1246 passed
(includes new pit-gate route regression test), frontend acceptance 212/212,
ruff clean on every touched file, and a 22-probe live battery against the real
DB (delete/gates_r2b_confirmed_2026-08-25/live_battery.py) covering all old
flows (S8 scans, PIT gate, research qty, data lane, R14 CA join, R6 top10,
evidence radar, hybrid-v2 overlay, feature registry lint ok=true, R0-B cohort)
plus the new guidance OMS flow and POST guards.

Defect found by the battery and fixed: GET /api/v1/selection/pit-gate returned
500 - pre-existing NameError (route used list_latest_selection_payloads with
no import in scope). One-line fix matching sibling routes; regression test
added; TWINS sweep found no other site. Live posture unchanged:
sourceActivationReady=false with named stale-last-good blockers until the
three lagging NSE sources go current; live orders stay triple-gated off.

## 2026-08-25 - File A R8 native core scanners (PK3) built + verified

New: scanners/registry.py (five versioned definitions, stable parameterHash),
scanners/native_core.py (run builder wrapping R5 claims; representative_matches
first-wins per group; correlated_possible twins; PK shadow isolated), routes
GET /api/v1/scanners/definitions + /native-core{,/{symbol}} + POST /scanners/run
405, S3 optional nativeCoreMatches attach (rows byte-identical, rank safe), S6
merge_native_claims empty-group-only ingest (routes do not inject this ticket).
Frontend: #nativeCorePanel in Live Ops + native-core.js?v=20260825-r8-1 +
adapter 17th fetch; copy "Native core - trade guidance, not an order."
Tests: test_r8_native_core.py 17 cases incl. no-place_order-under-scanners;
full backend 1263 passed; acceptance-check 214/214; live battery 24/24.
GATES: delete/gates_r8_native_2026-08-25/GATES.md all pass.
Hybrid sections opened per README §9.3 R8 row: §16.8 feature formulas,
§16.9 family caps / independence families, §15.4 trust combinations.

## 2026-08-26 - File A R10 pipe DSL (PK5/FUS-010) built + verified

New: scanners/pipe_dsl.py (two seeded named recipes, deterministic stage
in/out counts with capped reasons, zero emitted claims) + routes GET
/api/v1/pipes/{definitions,{pipe_id}/run} and POST /api/v1/pipes/run -> 405.
Frontend: #pipeLabPanel (Live Ops), pipes.js?v=20260826-r10-1, adapter fetch
#18 (/api/v1/pipes/definitions); panel self-fetches each run.
Tests: test_r10_pipes.py 17 cases (determinism, twin non-inflation,
invalid-stage fail-typed, ENRICH pass-through, zero-claims/no-place_order
source scan, route codes). GATES r10 all pass: G2 scope 63 passed; FULL
backend 1280 passed; acceptance-check 215 checks all green; live battery
26/26 incl. live pipe run confirmedCount=0.
Hybrid sections opened per README 9.3 for R10: Hybrid 16.9 family caps and
independence families (FUS-009 interplay); FUS-010 contract wording from
File A 21.13 amendment row plus the 25 CROSS table entry.

## 2026-08-25 - File A R11 MCX master readiness + swing gates built + verified

New: selection/r11_mcx_live.py (observed master/bars readiness enum incl.
WAIT_MCX_MASTER / WAIT_MCX_LOCAL_BARS / WAIT_MCX_STALE / WAIT_MCX_CALENDAR;
per-row lot/tick/expiry/dte/tender with named why-codes; triedSourceKeys),
routes GET /api/v1/selection/mcx-master{,/{symbol}} + POST x2 405,
swing_delivery_gate / swing_rs_gate gate-only helpers over S5/S3 semantics,
mcx_profile_blocker for future PRF-005/006/007 boards (still empty).
Frontend: #mcxMasterPanel + mcx-master.js?v=20260825-r11-1 (MCX segment
re-loads live status; never fixture gold), adapter fetch #19.
Tests: test_r11_mcx_live.py 11 cases (honest empty-spine WAIT, no invented
fields, tender veto, FBIL/CFTC cannot confirm/unlock, S5 intraday delivery
regression pin, route codes, no place_order). GATES r11 pass: G2 scope 41
passed; FULL backend 1291 passed; acceptance-check 216/216; live battery
27/27 incl. GET /api/v1/selection/mcx-master -> 200 confirmedCount=0.
## 2026-08-25 - File A R15 Scanner Lab UI built + verified

New: frontend/scanner-lab.js?v=20260825-r15-1 (inspector tab + Definitions/
Pipe flow/Symbol/PK shadow views), backend one-fetch BFF GET
/api/v1/scanners/lab-bundle (+POST 405) aggregating native definitions, both
seeded pipe runs and PK parity state with named inner codes. #scannerRunButton
relabelled "Refresh lab (GET)" and rewired to lab refresh (legacy scanner fire
disconnected). Adapter fetch #20 -> TrendForgeScannerLab.apply. Radar header
template pinned unchanged in acceptance-check (no column explosion).
Tests: test_r15_lab.py 3 cases; GATES r15 pass: G1 217/217, LAB_WIRED,
G3 s7 19 passed, FULL backend 1294 passed, live battery 28/28 incl.
GET /api/v1/scanners/lab-bundle -> 200 confirmedCount=0.
Latent defect fixed en route: main.py research-quantity error path referenced
SelectionState/EvidenceDirection that were never imported (NameError landmine,
same family as the earlier pit-gate bug); imports added. TWINS swept: no other
undefined-name sites flagged by ruff F821 in main.py after fix.
## 2026-08-26 - File A R13 remaining scanners built + verified (chips-only)

Superseded by the 2026-08-27 guidance-grade correction below. The original
per-symbol/raw-history, RSI reuse, close-range ATR, zero-JS, 1306-test and
29-probe statements are historical and must not be used as current evidence.

## 2026-08-27 - R13 guidance-grade closure reverified

- Six formula-pinned chips use one bulk query over hash-matched R5/R14 adjusted
  closed EOD bars. Missing identity, adjustment or lineage fails closed.
- Pure-Python Wilder RSI14; canonical BB20/KC EMA20/Wilder ATR10; confirmed
  VCP pivots and median dry-up <=0.70; symmetric reversal; explicit 10d/52w
  high/low with current-bar exclusion and 52w component pending.
- Additive guidance fields and `representative_guidance_chips` cannot mint a
  claim or change candidate direction, rank, S7 public state or confirmation.
- Scanner Lab carries the full native run; primary radar shows one guidance
  representative per family. S8 daily builds persist native hash + ids only.
- Verification: focused integration 60 passed; full backend 1320 passed;
  frontend 217/217; compile pass; read-only live battery 24/24.
- Runtime observation: 11 definitions; native-core 2,623 rows / 2,379 matched
  rows / confirmedCount=0; about 14-19s. Lab about 32-34s. Existing S8 stayed
  `WAIT_S8_LINEAGE`; the next authorized daily scan must persist the new hash.
## 2026-08-28 - R16 pre-migration implementation checkpoint

R16 is PARTIAL at a verified pre-migration boundary. The code contract is
implemented, but the live SQLite database has not received migration
0013_r16_pit_substrate and no populated replay exists. Therefore the current
runtime state is BUILDING / PIT_NOT_APPROVED with blocker
WAIT_R16_SCHEMA_NOT_APPLIED. Do not report R16_IMPLEMENTATION_VERIFIED or
production readiness yet.

Implemented: shared S8Service and post-R5 handoff; immutable R16 hypothesis and
outcome contracts; exact-cell metrics/policy; six-table normalized store and
migration code; CLI-owned schema/catch-up/status operations; read-only GET API
family; legacy PIT compatibility projections; dedicated backend-authoritative
R16 frontend with lazy observations; symbol/date-bounded A4 history reads; and
fail-closed same-date S8 conflict handling.

Verification: focused R16/pipeline/scanner suite 51 passed; complete backend
1,336 passed with one Starlette deprecation warning; complete frontend 218/218.
Read-only live-DB CLI and API observation returned zero R16 rows and the expected
schema blocker. Initial browser load requested PIT status and metrics but not
observations. The inspector-toggle request was not interactively observed
because the browser action approval service was unavailable; static acceptance
coverage remains green.

Remaining R16 gates: separate approval for live DB backup/migration, populated
catch-up, deterministic replay/idempotency, query plans and incremental
performance, restart/concurrency, API/UI observation of real rows, and honest
policy-floor evaluation. No probability, CONFIRMED, broker, order or executable
quantity authority was added.


## 2026-08-29 - R16 post-migration replay checkpoint

R16 v1 implementation is present for NSE cash EOD swing research. Before the
migration, an online SQLite backup was created at
`data/backups/trendforge_research_pre_r16_20260828_202421.db`; integrity was
`ok` and the 5,832,974,336-byte backup matched the source page count and page
size. Migration `0013_r16_pit_substrate` was then applied to the existing
research database. All six PIT tables plus worker state exist, foreign-key and
quick checks pass, and no pre-existing schema object was removed or changed.

The current complete S8 run is
`PRF-S8-SCAN-RUN_d8aa8fe3ac804e3fffe0359f` for 2026-08-28. It contains 678
rows, real S2/S3 lineage, no missing stage, S3 completeness 2,629/2,629 and
keeps source activation and confirmation authority false. The official NSE
index companion was refreshed as a populated `PARSED_STRUCTURED` artifact with
165 rows before this S8 was accepted.

Catch-up produced one immutable dataset, 2,034 hypotheses, 2,034 latest
observations, six exact-cell metrics and six approval-ledger rows. Two repeated
replays appended zero observations and retained revision hash
`7a0ba5a05c9a535ea64f424d6bc1c02e2840c5986a4271d64ed94df28030e0cc`.
Legacy and intermediate S8 artifacts remain immutable and are explicitly
rejected for missing identity or lineage; they were not rewritten.

Current runtime truth is `BUILDING / PIT_NOT_APPROVED /
DATASET_AND_REPLAY / INCONCLUSIVE`. One eligible date cannot satisfy the
history, fold, holdout, censor, resolved-observation or bootstrap floors.
`probabilityAuthorized`, `confirmationAuthorized` and `executionAuthorized`
remain false.

Verification: focused R16 tests 16 passed; complete backend 1,343 passed with
one Starlette deprecation warning; complete frontend 218/218 passed. Five PIT
GET routes returned 200 without changing table counts; their POST variants
returned 405. Live query plans used
`idx_pit_observations_dataset_status`,
`idx_pit_observations_hypothesis_latest` and
`idx_pit_metrics_cell_latest`; the requested-symbol/date A4 loader remains
bounded. Rendered browser inspection remains a tooling caveat because the
in-app browser runtime failed in the Windows sandbox helper. Static lazy-load
and no-client-approval contracts are green. This caveat does not change the
PIT_NOT_APPROVED ceiling.




## 2026-09-03 - CROSS-015 / TDG-GAP-022 unified tradability gate

The research tradability gate is implemented across the selection spine. One
versioned `TradabilityResultV1` evaluates T2T, ASM, GSM, ESM, price band,
market halt, security active/suspended status, auction, F&O ban, MWPL and MCX
instrument/expiry/delivery mechanics under separate NSE intraday, NSE swing
and MCX profile policies. `REJECT` outranks `WAIT`, and both override an S7
confirmation candidate. `PASS` is non-voting and cannot create CONFIRMED.

`selection/tradability.py` owns source-state normalization, cadence-aware
freshness, deterministic component/result hashes and fail-closed policy.
`s7_state_gates.py` enforces the result; `s8_service.py` builds one batch;
`s8_persist_run.py` preserves the batch hash, component reasons and lineage.
Read-only endpoints expose the batch and per-symbol result. The S7 evidence
inspector shows the outcome and component table without calculating state in
JavaScript.

Observed proof: focused backend 53 passed; full backend 1,474 passed; frontend
220/220 passed; coverage 155 rows with zero drift. A direct current-source run
for INFY and TATASTEEL returned WAIT with explicit stale/missing components. The
HTTP S7 route currently remains blocked upstream by `R5_STRUCTURE_NOT_READY`.
No source activation, vote, probability, broker, order or execution authority
was added. Overall production readiness is not claimed.

### 2026-09-03 acquisition closure for ESM, price bands and auction

The three previously missing acquisition contracts are now wired through the
existing collector, parser, immutable object store and last-good path. No
second downloader or database was added:

- `nse_esm`: official NSE `reportESM`; 290 normalized rows dated 2026-09-03.
- `nse_price_bands`: official dated `sec_list_DDMMYYYY.csv`; 3,517 normalized
  rows dated 2026-09-02.
- `nse_auction_securities`: official periodic-call-auction workbook; explicit
  `NIL` parsed as `VALID_EMPTY`, zero security rows, dated 2026-07-09.

The registry is now pinned at 126 jobs. Refresh writes canonical normalized
last-good objects; `load_restriction_sources()` reads those same objects for
the unified gate. Bare HTTP 200, HTML, wrong schema, unknown bands and an empty
auction workbook without `NIL` fail closed and cannot replace last-good data.
Price-band rows currently prove band classification only. A banded symbol
without exact lower/upper limits remains `WAIT_PRICE_BAND_VALUES_MISSING`.

Verification after the source-map v3 re-pin: focused acquisition, registry,
compiler and tradability tests 67 passed; complete backend 1,485 passed;
frontend 220/220 passed. Current
runtime loader observation reproduced POPULATED 290, POPULATED 3,517 and
VALID_EMPTY 0 respectively. Source activation and gate-authorized counts remain
zero; this milestone does not make the whole product production-ready.

## 2026-09-04 - Build plan recorded for the three blocked parts (PLAN only, no code changed)

Plan files: `docs/fable/remaining_build/THREE_BLOCKERS_BUILD_PLAN_2026-09-04.md`
(sequencing/ownership/gates + deep-plan council verdict) and
`docs/fable/remaining_build/PRICE_BAND_TECHNICAL_ZONES_BUILD_PLAN_2026-09-04.md`
(16 sections: NSE rule matrix with primary citations, calculation contract,
feature contracts, gate pseudocode, coding style, 50 adversarial tests).
Verified during planning: the band/ESM/auction checkpoint is real in the
normalized store (hashes pinned in the plan); R5 and activation gaps are
data-ops/governance consequences. Recorded as D-068. No tests were run for
this entry because no code changed.

## 2026-09-04 - Plan audit amendments (tester pass, plan-doc edits only)

AGI-tester audit of the three-blocker plan found and fixed 4 gaps, recorded
as D-069: (1) Part 2 named five lineage inputs, the `_hash_matched_r5_or_503`
guard compares seven — plan now lists all seven; (2) no code path grants
`gate_permission=True` anywhere, so activation was unachievable even with
fresh data — plan now requires the human-review grant record/contract to be
designed first; (3) the five R2-B confirm-path source keys are now named with
per-window re-checks; (4) added fixture-vs-live boundary rule, 4-row operator
approval matrix, effort CIs and fail-closed rollback notes. No code changed;
no tests run for this entry.
