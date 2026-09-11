<!-- CURRENT_STATE_HISTORY_BOUNDARY: requirement-1 -->
> **Current code/readiness summary (reviewed 2026-09-07): [CURRENT_STATE.md](CURRENT_STATE.md).**
> This file retains dated technical notes and historical observations below.
> Older phrases such as "current", "not implemented", "next" or "passed" describe
> their recorded checkpoint, not today's code, database, freshness or permissions.
> File A remains plan authority. Historical counts never grant runtime activation.

## 2026-09-11 - 03D publication and exact-head acceptance

Accepted source commit: `fce62874a61e4e2bb6d939bef6d0811e5a266996`.
Its Git tree `9295187c49ee7fe5f5005d6ec42a92f94775dcf8` exactly matches the
locally tested repair. PR #6 remains open and unmerged.
[CI 34496385997](https://github.com/onlyvictus-bit/trendforge/actions/runs/34496385997)
completed / success on that head. The GitHub job logs were inspected directly:

| Check | Observed result |
| --- | --- |
| Backend job 102935794979 | 1699 passed, zero failures/skips, two dependency warnings; 247.16 seconds |
| Python compile / Ruff | Passed / All checks passed |
| Frontend job 102935795027 | Passed; 220/220 primary checks and all additional suites |
| Dependency install | Exact xlrd 2.0.2 installed |
| Mypy job 102935794982 | Known non-blocking failure: 512 errors / 70 files |
| Normalized Mypy delta against accepted 03C | Zero new/removed errors or notes in the same local environment |

The workflow's existing non-blocking Mypy policy was not weakened. Overall CI
success does not mean Mypy is clean. The same acceptance source was rechecked
via GitHub on 2026-09-11. Documentation-only follow-up heads require their own
CI; `fce62874` remains the actual 03D implementation acceptance checkpoint.
03D: IMPLEMENTED + TESTED. 03E: NEXT / UNLOCKED. 03F: GATED on 03E.
Full R-HIST-03: NOT COMPLETE. LIVE-DATA-VERIFIED / PRODUCTION-ACCEPTED: NO.
Only scratch databases were used; no real migration or trading action occurred.

## 2026-09-10 - PR #6 repair verification (historical local checkpoint)

Baseline: `6de1e14973edcf62b61c9b6a1441214ace656ec4`, with the original three
failures confirmed from CI run `34486533849`. Two R18 failures reproduced
locally. Additional failing tests exposed missing recovery/crash points,
legacy-event misclassification, concurrent finalizer and dispatch races,
wrong indexed identity acceptance and concurrent authority registration.

Checks run from the isolated checkout's `backend` directory, using the existing
Python 3.14.3 environment and user-approved isolated `xlrd==2.0.2`:

```sh
python -m compileall -q trendforge_api tests
python -m pytest -q -p no:cacheprovider tests/test_rhist03d_ml_history.py
python -m pytest -q -p no:cacheprovider tests/test_rhist03d_recovery.py tests/test_rhist03d_artifact_retention.py tests/test_retention_producer.py tests/test_retention_evidence_safety.py
python -m pytest -q -p no:cacheprovider --tb=short -rs --durations=8
python -m ruff check trendforge_api tests
python -m mypy trendforge_api --ignore-missing-imports --no-incremental
```

Each pytest invocation uses its own explicit writable scratch `--basetemp`.
No production database or source cache was migrated. The same local environment
checked actual 03C source at `2079336768907cf9f0668a8798cd631007c6e74f` for a
normalized per-file diagnostic multiset comparison (source coordinates and
embedded line references removed; errors and notes retained).

Observed checkpoints: repaired ML suite 28 passed; five original 03D suites
54 passed; expanded 03D matrix 72 passed; registration/retention regression
48 passed; final forced race checks 3 passed. Mypy: 512 errors in 70 files on
both revisions, zero new/removed normalized diagnostics on final repaired
source. Ruff/compile and frontend npm test passed after documentation updates.
The final full backend run on repaired source finished with **1699 passed,
zero failed, zero skipped, one Starlette deprecation warning**, in 904.25 seconds.
Earlier interrupted runs are not completion evidence. The final source passed
compilation and Ruff; frontend passed 220/220 primary checks and every additional
suite, including documentation contracts.

Official EIA XLS: 104448 bytes with OLE signature, eight populated numeric
records dated 2026-09-04 with xlrd 2.0.2. Masking xlrd against the identical
workbook reproduces WAIT_SCHEMA_MISMATCH. The CSV route also parsed eight rows,
but returned a null parsed date; CSV freshness is not verified by this result.

Post-publication exact-head CI remains pending. See
[the execution record](fable/RHIST03D_PR6_REPAIR_2026-09-10.md). 03D remains
IN PROGRESS; LIVE-DATA-VERIFIED (03D): NO; PRODUCTION-ACCEPTED: NO.

## 2026-09-09 - R-HIST-03C local verification evidence

Repository baseline: `fc236893b1504b857513fb896b8cb89050e17ffd` (tested 03B),
implementation branch `feat/rhist03-producer-wiring`, existing PR #6. Execution
used an isolated Python 3.13 environment with this repository's pinned
`backend/requirements-dev.txt`, including Ruff 0.15.5 and Mypy 1.19.1. Local Node
was 22; repository CI separately uses Python 3.14 / Node 24. Test fixtures use
real SQLite, market object bytes, HRA, publication and outbox; they are not live
trading-data verification.

Safety-first red/green evidence: the first 34 new tests failed before the
implementation. Worker, rebuild and predecessor-tamper tests also failed before
their corresponding fixes. The final new file contains 57 adversarial cases.

Commands from `backend`:

```sh
python -m pytest -q tests/test_r16_retention.py tests/test_r16_pit.py tests/test_s8_retention.py tests/test_retention_producer.py tests/test_retention_publication.py --tb=short
python -m pytest -q -rs --tb=short
python -m ruff check trendforge_api tests
python -m compileall -q trendforge_api tests
python -m mypy trendforge_api --ignore-missing-imports
```

Observed focused result: **92 passed, 2 warnings**, comprising 57 new 03C tests
plus 35 existing R16/retention tests. Full backend: **1,621 passed, 2 skipped,
2 warnings**. The two existing network-dependent DGCIS and EIA tests skipped
because this local execution environment could not resolve their hosts. No new
03C test was skipped. Ruff and compilation passed. `cd frontend && npm test`
passed, including the existing history/current-state documentation contracts.

Mypy is NOT green: unchanged non-blocking legacy baseline, **512 errors across
70 files** at this implementation versus **513 errors across 70 files** on the
original backend. A per-file diagnostic multiset comparison (normalizing source
line coordinates, including embedded line references) found **zero new
diagnostics** and one removed old public-state Literal error. The new retention
module has no Mypy errors. Do not substitute the workflow's non-blocking success
for a claim of type-check cleanliness.

Coverage includes exact/missing/wrong/tampered S8 parents, real S8 payload
sealing, refusal to backfill unsealed legacy parents, all non-trade populations,
separate outcome evidence and time, duplicate replay, immutable revision chains,
linked rebuild versions, source-correction isolation, read-only fail-closed
proof checks, old decision/outcome/revision survival through actual cleanup,
transaction rollback, authority failure, crash after registration before
acknowledgement, and crash between an outcome and its explicit revision.

This entry records local evidence only. Exact final PR-head backend/Ruff,
frontend and baseline-aware Mypy results must be verified on PR #6 before
declaring **R-HIST-03C = IMPLEMENTED + TESTED**. 03D/E/F, the full R-HIST-03 gate,
R-HIST-04, live-data verification and production acceptance are not implied.

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

# Validation

## CROSS-004 / TDG-GAP-014 profile-source validation - 2026-09-02

    Profiles:                       PRF-001..007 (7/7)
    Mandatory/confirm/veto keys:    NAMED
    Registration vs data-ready:     SEPARATE
    Missing intraday bars:          EXPLICIT
    Delayed context as live proof:  FORBIDDEN
    Source activation/confirmation: FALSE / FALSE
    Read-only API:                  HTTP 200
    Focused:                        5 passed
    Complete backend:               1,458 passed, 1 warning
    Python compilation:             passed
    Frontend acceptance:            219/219

This contract names dependencies. It does not prove current data, activate a
source, score a candidate, emit CONFIRMED, calculate quantity or execute.

## R0-C quarantine validation - 2026-09-02

    Compiler partition:             VERIFIED
    R0-B/R0-C overlap:              ZERO
    Missing compiled contracts:     ZERO
    R0-C reviewed/voting/gates:     0 / 0 / 0
    Unexpected gate permission:     FAILS CLOSED
    Read-only API:                  HTTP 200
    Focused R0-C:                   4 passed
    Complete backend:               1,453 passed, 1 warning
    Frontend acceptance:            219/219

The API exposes the compiler-derived remainder only. It does not activate a
source, produce CONFIRMED, authorize execution, or prove production readiness.
R0 remains PARTIAL for source-specific proof and activation work.

## R18 model governance validation - 2026-09-02

    Contracts and hashes:           VERIFIED
    PIT folds, embargo, holdout:    VERIFIED
    Costs, calibration, net R:      VERIFIED
    Automatic promotion:            FORBIDDEN
    APPROVE under R16 WAIT:         BLOCKED
    Human REJECT contract:          VERIFIED
    Drift demotion and rollback:    VERIFIED
    Governance GET:                 HTTP 200
    Runtime state:                  MODEL_NOT_APPROVED
    R16 state:                      PIT_NOT_APPROVED
    Dataset age:                    5 days
    R18 schema:                     WAIT_R18_SCHEMA_NOT_APPLIED
    Probability/win/performance:    HIDDEN/HIDDEN/HIDDEN
    R18 focused:                    14 passed
    Complete backend:               1,449 passed
    Frontend acceptance:            219/219
    Full frontend command:          passed

No live migration, model training, promotion, broker call, order, account access or execution occurred. The review POST was fixture-tested against temporary databases and was not invoked against live storage.

## Documentation reconciliation check - 2026-09-01

    R3 implementation:             PRESENT (selection/r3_live.py)
    R14 implementation:            PRESENT (selection/r14_live.py)
    R16 implementation:            PRESENT (pit/store/service/metrics + frontend)
    R16 approval state:             PIT_NOT_APPROVED
    R17-G state:                    POSTPONED_BY_USER
    R18 implementation:            NOT PRESENT
    Next coding milestone:          R18-A
    Required runtime ceiling:       MODEL_NOT_APPROVED

This is a documentation-to-code reconciliation, not a new regression run. No R18 behavior, model promotion, probability, performance or production-ready claim is validated here.

## R17-G postponement and R18 handoff - 2026-09-01

```text
R17-B-F and R17-H/I:          FIXTURE_VERIFIED
R17-G approved attempt:       BLOCKED at first quote
TrendForge interval repair:   60m accepted; 25 focused tests passed
Exact OpenAlgo identities:    10/10
Broker quote result:          no data; stored Kite session invalid
User disposition:             POSTPONED_BY_USER
R9 ORB/VWAP:                  POSTPONED_NO_VERIFIED_INTRADAY_BARS
Next active milestone:        R18-A MODEL_GOVERNANCE_FOUNDATION
Current R16 authority:        PIT_NOT_APPROVED
Required R18 runtime ceiling: MODEL_NOT_APPROVED
```

This handoff changes work selection, not verified runtime capability. The last
complete regression evidence remains 132 focused R17/OpenAlgo tests, 1,435
backend tests and 218/218 frontend acceptance plus the R17 shadow check. R18
may be fixture-built against the R16 substrate, but no model promotion,
probability/performance UI or execution claim is valid until the independent
PIT/OOS gates pass.
## R17-G approved live observation - blocked 2026-09-01

```text
OpenAlgo REST service:           listening on 127.0.0.1:5000
OpenAlgo WebSocket service:      listening on 127.0.0.1:8765
Exact NSE identities:            10/10
Intervals response:              HTTP 200; D, 1h, 1m, 3m, 5m, 10m, 15m, 30m, 60m
TrendForge interval defect:      fixed; 60m accepted
RELIANCE quote response:         HTTP 500; no populated data
Observed broker error:           Incorrect api_key or access_token
Replay rows:                     0
Stream observation:              not reached after REST fail-closed
Capability state:                BLOCKED / FIXTURE_VERIFIED
activationEligible/executable:   false/false
Interval/REST focused tests:     25 passed
Focused R17/OpenAlgo tests:      132 passed, 1 warning
Complete backend:                1,435 passed, 1 warning
```

The observer used only the approved local read-only market-data routes. Its
report contained no credential and it could not activate a data lane. HTTP 200
for intervals counted only because structured interval data was populated.
The HTTP 500 quote produced no usable market evidence and no latest-good/replay
write. A fresh Kite login is required before REST, WebSocket, reconnect and
replay proof can continue.
## R17-G OpenAlgo runtime preflight - 2026-09-01

    Runtime:                       D:\openalgo\.venv
    websocket-client:              1.9.0
    Exact bounded identities:      10/10
    Equity classifications:        10/10
    Populated tokens:              10/10
    Credential/network/socket use: none

This proves local dependency and identity compatibility only. It is not live
REST, stream, reconnect or replay evidence.
## R17-G bounded observer fixture verification - 2026-08-31

    New focused observer:          11 passed
    R17/OpenAlgo focused:          132 passed, 1 warning
    Complete backend:              1,435 passed, 1 warning
    Frontend:                      218/218 + R17 shadow check
    Python compilation:            passed
    Real OpenAlgo master:          NSE:RELIANCE = EXACT / EQUITY
    Missing-credential CLI:        BLOCKED / FIXTURE_VERIFIED

The observer was exercised with deterministic REST/WebSocket fixtures for one
symbol, a ten-symbol boundary, shortlist subscription, close-on-error,
reconnect/resubscribe, exact subscription acknowledgement, partial REST and
partial stream failures, secret redaction and raw/normalized replay hashes.
The real OpenAlgo symtoken database was opened read-only and exact identity was
observed without reading credentials or contacting a broker.

The credentialed run was not performed. The local service was not started and
the encrypted API key/broker session was not used because that concrete action
still requires explicit informed approval. Provider sequence remains
unavailable, so even a future successful socket observation cannot by itself
prove gap-free continuity or authorize execution.
## R17-D-F and R17-H/I fixture verification - 2026-08-31

```text
Focused:
  tests/test_r17_openalgo_contract.py
  tests/test_r17_openalgo_rest.py
  tests/test_r17_openalgo_identity_replay_stream.py
  tests/test_r17_openalgo_shadow.py
  tests/test_q5_openalgo_boundary.py
  tests/test_dual_lane.py
Result:                       110 passed, 1 warning

Complete backend:             1,424 passed, 1 warning
Frontend:                     218/218 legacy checks + R17 shadow check
Python compilation:           passed
```

Observed through `TestClient`:

```text
OPENALGO_ENABLED absent:
  GET /api/v1/integrations/openalgo/shadow -> 200
  activation.stage                         -> DISABLED
  rows                                     -> []
  networkAllowed/storageAllowed            -> false/false
  executable                               -> false

OPENALGO_ENABLED=1 and OPENALGO_RO requested:
  shadow activation.stage                  -> FIXTURE_VERIFIED
  shadow blocker                           -> WAIT_REST_OBSERVATION
  effective data lane                      -> FREE_OFFICIAL
  canConfirm/executable                    -> false/false

POST /api/v1/integrations/openalgo/shadow  -> 405
```

Adversarial coverage includes disabled runtime activity rejection, unchanged
base hashes on rollback, stream stop, configuration-not-live, REST replay
requirements, absent provider sequence, exact identity, stale REST, crossed
and partial chains, non-F&O `NOT_APPLICABLE`, PCR zero denominator,
unsigned-gamma labelling, one-root concentration, cost-aware quantity and
lot-safe notional. This is fixture proof only. No credential, provider
network, live master, broker account, order, socket or production storage was
used. The post-build secret-free capability report returned `ABSENT`,
`configured=false`, `enabled=false` and blocker
`OPENALGO_CONFIGURATION_ABSENT`.

## R17-C OpenAlgo REST client - 2026-08-31

```text
Focused:
  tests/test_r17_openalgo_rest.py
  tests/test_r17_openalgo_contract.py
  tests/test_openalgo_client.py
  tests/test_openalgo_ohlcv_adapter.py
  tests/test_q5_openalgo_boundary.py
Result:                       59 passed, 1 warning

Complete backend:             1,373 passed, 1 warning
Frontend acceptance:         218/218 passed
Python compilation:          passed

Fixture observation:
  documented IST input:       2025-04-01 09:15:00+05:30
  canonical UTC output:       2025-04-01T03:45:00+00:00
  exact multiquote LTP:       101.0
  routeCount:                 8
  clientImplemented:          8
  contractHash:               8cff83dc22937cf69ac6240a30cfcadc6d5cfff2040b01696a9da31651e7a3b9
  executable:                 false
```

Adversarial fixtures cover numeric-string/naive timestamps, valid-empty
history, malformed and non-finite values, impossible OHLC, negative volume,
duplicate/reversed candles, missing/stale quote timestamps, partial/wrong
multiquote identity, response limits, bounded transient retry, per-route
circuits, pacing and API-key redaction. No live OpenAlgo server, broker account
or credential was used. The result is fixture verification, not `SHADOW_LIVE`,
replay proof or production readiness.

## R17-B OpenAlgo provider contract - 2026-08-31

Historical checkpoint; superseded by the R17-C route states and contract hash
above.

```text
Focused:
  tests/test_r17_openalgo_contract.py
  tests/test_q5_openalgo_boundary.py
  tests/test_openalgo_client.py
Result:                       31 passed

Complete backend:             1,348 passed, 1 warning
Frontend acceptance:         218/218 passed
GET /api/v1/integrations/openalgo/contract:
  status:                     200
  schemaVersion:              trendforge.openalgo-provider-contract.v1
  providerCommit:             24f8d395372799066a24ba1d6311f0e7791555d8
  routeCount:                 8
  providerFileHashCount:      11
  clientImplemented:          4
  contractPinned:             4
  streamContinuityState:      STREAM_SEQUENCE_UNAVAILABLE
  executable:                 false
```

The endpoint performs no OpenAlgo I/O and contains no API key. It is contract
evidence only. It does not prove live broker data, replay integrity,
`SHADOW_LIVE` or production readiness.

## S9 PIT homework UI + backend - 2026-08-25

```text
tests/test_s9_pit_homework.py:   7 passed
Frontend acceptance:            209/209 (incl. 5 S9-specific needles)
Live GET /pit-homework:         200, validationStatus=PIT_NOT_APPROVED
confirmedCount:                 0
```
Observations carry STO-017 status, MFE/MAE, censor reason. No win-rate,
no performance chart, no auto-trade. `ATR_MISSING` when insufficient bars.

## Dual-lane + research quantity UI wiring - 2026-08-25

```text
Backend modules: selection/data_lane.py, selection/research_quantity.py
tests/test_dual_lane.py: 11 law tests (default FREE, blocked ON, LONG/SHORT, caps)
GET  /api/v1/settings/data-lane
POST /api/v1/settings/data-lane     preference only; execution stays false
GET  /api/v1/selection/research-quantity
POST /api/v1/selection/research-quantity  405
Frontend: data-lane.js + research-quantity.js mounted; adapter fetches both
```

Ceiling: research screener. `sourceActivationReady=false`. No place_order.

## File A S8 persist-one-reconstructable-scan - 2026-08-25

```text
tests/test_s8_persist_run.py:            8 passed
Focused regression (S4–S7+R5):          39 passed
Live isolated uvicorn :8018:
  GET  /api/v1/selection/scans/latest    → 200; runId prf-s8-scan-run_2e37…;
       confirmedCount=0; rows=503; states={WAIT}; lineage keys present
  GET  /scans/{run_id}                   → identical publicStates
  POST /api/v1/selection/scans           → 405
```
STO-006 immutability + STO-008 state events exercised via store helpers on
the existing tables (no second database). Ceiling
`LIVE_S8_RECONSTRUCTABLE_WAIT_ONLY`.

## Production-research audit - 2026-08-25

```text
Full backend pytest:        1,180 passed / 0 failed / 0 errors
  (before ticket: 1,174 passed / 6 failed — all six STALE_FIXTURE, fixed)
Focused spine (S2–S7+R5+R14): 100 passed
Frontend acceptance:        197/197
Live battery (fresh :8000): 15 GET routes 200 or named-404;
  confirmedCount=0 on S3–S7; POST s7/s6/s4 = 405;
  named-activation: sourceActivationReady=false, authorizedCount=0
Safety grep:                usage-level SELECTION_CLEAN; guard doc-mentions present
Artifacts:                  delete/gates_prod_audit_2026-08-25/pytest_full_after.txt
```

Verdict: **PRODUCTION_RESEARCH_READY** (research screener ceiling only —
no broker, no CONFIRMED, no qty, no PIT_APPROVED).

## Audit round: /s6-resolution merged feed + shortlist bounding - 2026-08-24

```text
S6 suite (14 tests incl. bounding + merged feed + real pipeline assembly): 14 passed
Combined regression (s6 + q5 resolver + radar + r5 + r6):                 69 passed
Full backend suite:                                     1162 passed / 6 failed (pre-existing, unrelated: hybrid overlay 503 test, fno-ban date clamp, market_data_service x3, vyom resolver)
Frontend acceptance:                                              193/193 checks passed
```

Observed: bounded board excludes claim-less rows (universe 0 vs wide 1 on the
same lineage); injected cash FTR-040 at strength 0.95 becomes THE participation
representative over R5's RVOL claim (0.833); real pipeline assembly mints
FTR-040 at attention priority 0.9 with no CASH_FEED warning; thin /resolution
route byte-for-byte unchanged.

## S6 claim-feed widening (R5 claims → FUS-009 feed) - 2026-08-24 evening

```text
tests/test_s6_claim_feed.py:                       7 passed
Focused (s6 + r5 + q5 resolver + r1 + m_factor):  38 passed
Full backend:                                  1,137 passed / 6 failed
  (same six pre-existing transport/parser failures; none new)
Frontend acceptance:                             189/189 passed
```

Observed: R5StructureRowV1 publishes minted `claims`/`facts`; boundary
validator rejects confirming claims; old payloads without new fields load;
`merged_feed` dedupes by claim_id (first wins); `market_context` attach is
display-only and `canSupportConfirmed=false` enforced at model validation.
Run-hash widens across the v1→v2 boundary (deterministic per version).
Callers opt in — no route behavior changed in this ticket.

## S4 structure pack + S5 shortlist enrichment + S6 family resolution - 2026-08-24

```text
S4 gate suite (s4 pack + r5 + r14 + s2 regression): 47 passed
S5 gate suite (s5 pack + r6 + top10 + r5 + s2):     46 passed
S6 gate suite (s6 + q5 resolver + radar + r5 + r6): 66 passed
Adjacent suites sharing main.py (api/live panels/feature registry): 104 passed
Frontend acceptance: 193/193 checks passed
```

Observed behaviour: S4 GET returns WAIT packs with r14RunHash lineage,
confirmedCount=0 and POST 405; unclosed/WAIT_CA rows carry no structure claims;
breakout+trend acceptance collapse to one CG_PRICE_STRUCTURE representative.
S5 rows never exceed the shortlist; delivery is forbidden on intraday horizons;
missing chains yield UNKNOWN_NEEDS_R12 with score 0. S6 required families swap
when the injected profile object swaps; conflict flags without CONFIRMED;
lineage mismatch is 503. Limitations: S5 options package remains a stub until a
fresh chain contract exists; S6 votes only on lineage-backed claims (R5-minted)
plus explicitly injected feeds; enrichment fields stay context notes.

## S3 cheap discovery - 2026-08-24

```text
Focused S3 suite: 10 passed, 1 Starlette/httpx deprecation warning
Related S2/R2/R5/R6/radar/S3 backend suites: 76 passed
Frontend suite: 186/186 acceptance checks; S3 renderer and adapter passed;
  24 inventory-workbench files verified
Complete backend suite: 1,123 passed, 6 failed, 1 warning
```

The six complete-suite failures remain outside S3: hybrid overlay empty-DB
isolation, F&O-ban fake transport signature, three market-data-service fixture
contracts, and Vyom resolver fake callback signature. They prevent a
production-readiness claim but did not fail the S3 focused or related suites.

Read-only runtime observation with collectors disabled:

```text
GET /api/v1/selection/cheap-discovery
  200; schema trendforge.s3-cheap-discovery.v1
  eligible=2633 scanned=2633 excluded=0 failed=0 unattempted=0
  completeness=1.0 partial=false confirmed=0 deliveryQueried=false

GET /api/v1/selection/cheap-discovery/watch?limit=5
  200; schema trendforge.s3-watch-queue.v1
  totalWatch=1824 shown=5; every returned row state=WATCH
```

Adversarial coverage proves full-universe scanning above 40 rows, deterministic
RVOL/NR7/RS, explicit unknown optional sources, cash-only OI non-penalty,
lineage fail-closed behavior, partial-scan WAIT, WATCH-only queue filtering,
no delivery query, no R2 mutation, POST 405, and zero CONFIRMED.

## S2 market weather - 2026-08-22

- tests/test_s2_market_weather.py 11 passed (incl. live-leak regression + stale-sector recompute + mcx_bhavcopy key) (incl. live-leak variation-points regression) (T1-T10: honest percent, official
  key wins, reject-to-null, VIX band not direction, breadth UNKNOWN never 0/0,
  official sector ranks no yfinance, local-MCX vs grey global, ceilings,
  routes 405/503).
- Combined regression radar+r5+r6+top10+r14+r2b+a5 **94 passed**.
- Frontend acceptance-check **181/181** (s2 strip + scripts mounted).
## R1-R14 current-status verification - 2026-08-23

```text
Focused R1-R6/R14 backend suites: 111 passed, 1 Starlette/httpx warning
Frontend contract/acceptance/live-adapter/workbench suite: 176/176 passed;
  R1/R2 exclusive adapter passed; 24 workbench files verified
Complete backend suite: 1,096 passed, 6 failed, 1 warning (208.30s)
  Failures are outside focused R1-R6/R14 suites and still block production readiness
```

Read-only runtime observation against `127.0.0.1:8000`:

```text
R1 /api/v1/selection/evidence       200; 123 source contracts; 2,633 stocks
R2 /api/v1/selection/attention      200; 1,824 WATCH; 809 WAIT; 0 REJECT
R3 /api/v1/selection/resolution     200; 2,633 rows; WAIT; 0 CONFIRMED
R4 /api/v1/selection/identity-pin   200; 2,633 rows; LIVE_ID_PIN_WAIT_ONLY
R5 /api/v1/selection/structure      200; 2,633 rows; LIVE_WAIT_REJECT_ONLY
R6 /api/v1/selection/enrichment     200; 40 rows; RESEARCH_SHORTLIST_NOT_CONFIRMED
R14 /api/v1/selection/ca-join       200; 2,633 rows; LIVE_CA_JOIN_WAIT_ONLY
sourceActivationReady=false on every observed selection surface that exposes it
```

Verdict: R1-R6 and R14 are usable for fail-closed research at their explicit
ceilings. R7 is usable only as an offline developer harness. R8, R10 and R13
have bounded guidance-only implementations; R9 remains skipped and wider
R11/R12 work does not make R8-R15 a complete production sequence. Passing
suites does not prove profitable or production-ready trading behavior.

## M-Factor usefulness: R5 claims into FUS-009 - 2026-08-23

```text
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_m_factor_claims.py tests/test_m_factor_bff.py -q
  -> 26 passed
full backend suite -> 1071 passed / 6 failed (documented pre-existing set)
cd D:\TrendForge\frontend && npm test -> 176/176
ruff (m_factor_claims.py, m_factor_bff.py, tests) -> All checks passed
```

Live probe `build_m_factor_batch(horizon="swing", side="both", limit=40,
debug=True)` on the real 2026-08-21 lineage (universe 2633):

```text
boards: BUY 40 / SELL 40 / WAIT 40   (2026-08-22 baseline: BUY 40 flat, SELL 0)
rank tiers: 0 | ~11-25 participation-only | 50.7-55.0 structure+participation
BUY top-40 rank min/max: 54.75 / 55.00  (saturation = binary FTR-006 accept)
SETUP_READY in capped DTO: 95/120, each backed by a selected STRUCTURE support claim
example BUY  AEROENTER long 55.0 / short 0.0  Bull  SETUP_READY  WAIT
example SELL AADHARHFC long 0.0 / short 55.0  Bear  SETUP_READY  WAIT
STRUCTURE family support_strength 1.0 on FTR-006 rows; PARTICIPATION maxes
  FTR-040 vs FTR-017 in CG_ACTIVITY_SESSION (no sum)
how cites FTR-006/FTR-017 claim ids; what = UNKNOWN_NO_LARGE_DEAL_ROW (no named deals)
r3EvidenceStrength per row (thin persisted R3, e.g. 23.58 vs fused 55.0)
entry/stop/t1/t2/quantity null; publicState never CONFIRMED
intra WAIT_HORIZON_INTRADAY_NOT_ACTIVATED empty; position/commodity empty; POST 405
index: nifty50_change_percent parsed as 20.15 -> INDEX_CHANGE_SUSPECT,
  INDEX_CONFLICT_V0 unproven (sanity bound +/-7%), no conflict seats minted
mixed hashes still 503 WAIT_MIXED_SNAPSHOT / R3_RESOLUTION_NOT_READY
cold build ~16.5s (R5 rebuild across setup rows); cached ~5ms (30s TTL)
```

Browser (claimed user tab, ?v=20260823-mf4): live hero (real run id, WAIT
chip), BUY cards with long 55 / SETUP_READY, selected-card FUS-009 family
bars render real S_f/O_f (0-100), HOW line cites FTR-006 + FTR-017 claim ids
and reference level 135.97 as a research label, rank table shows
AEROENTER Bull 55/0 SETUP_READY WAIT. No fixture strings; no NaN (fixed a
camelCase alias bug in the family renderer). The guest could not complete a
side-toggle click (background-window actionability); SELL rendering uses the
same card path as BUY and sellRows were verified in the API payload.

## M-Factor live BFF + live tool room - 2026-08-22

```text
backend/tests/test_m_factor_bff.py           16 passed
full backend suite                           1051 passed / 7 failed (pre-existing baseline)
frontend acceptance-check                    175/175
frontend selection-live-adapter + workbench  passed
ruff (new/changed files only)                All checks passed
```

Live observation against the running server (127.0.0.1:8000, real
2026-08-21 EOD lineage, universe 2633, advancers 1307 / decliners 1273):

```text
GET /api/v1/tools/m_factor?horizon=swing   200; runId m-factor-bff_*;
  r1/r2/r3 hashes present; stateCeiling WAIT; sourceActivationReady=false;
  ALLCARGO long 24.93 / short 0.0 (0.25 PARTICIPATION weight cap visible);
  readiness SETUP_READY from real R5 CLOSED_BAR_BREAKOUT setup; levels null
GET ...?horizon=intra                       200; horizonWaitCode
  WAIT_HORIZON_INTRADAY_NOT_ACTIVATED; buy/sell/wait boards empty
POST /api/v1/tools/m_factor                 405
```

Browser (in-app browser, claimed user tab at http://127.0.0.1:8000/):
M-Factor tool room painted the live view - eyebrow
"SWING EOD RESEARCH - LIVE R3 FUS-009", RUN chip with the real BFF run id
(not FIXTURE-20260729-1042), live Signals content (market strip, bars,
rank table, ALLCARGO BUY card with PENDING levels) and zero
"ILLUSTRATIVE FIXTURE" tags inside #toolContent.

Re-verification after the "still old data" report (stale cached scripts
kept their old ?v= cache-busters; bumped to ?v=20260822-mf2, live panel
now marked data-mf-live=1 and self-reclaiming via MutationObserver, BFF
batch cached per lineage with a 30s TTL, cache disabled under pytest):

```text
GET swing cold 6.8s -> cached 5ms; intra 8ms; POST 405 unchanged
hero: chip WAIT; RUN m-factor-bff_26a6c8659fff28f64edc400b; data-mf-live=1
#toolContent: zero 168.9 / FIXTURE-20260729-1042 occurrences
tab clicks observed live: track (PIT_NOT_VALIDATED, 0 rows), engines
(FUS-009 ONLY RANK OWNER), signals round-trip
```

Known pre-existing full-suite failures (unchanged by this milestone,
previously recorded as a 20-21 fail baseline):
tests/hybrid_v2/test_api_overlay.py empty-DB isolation,
test_evidence_radar.py cross-test pollution (passes 19/19 in isolation),
test_failed_15_source_repairs.py fno-ban clamp, test_market_data_service.py
x3 fixtures, test_vyom_source_resolution.py refetch.

## Evidence radar + R6 shortlist + top-10 - 2026-08-22

- tests/test_evidence_radar.py 28 passed (C1-C19 + calculate-fill tests: coverage nothing-skipped,
  alias one-vote, companion, market-FII grain, unnamed deal, third-party zero,
  AMFI/SHP delayed, no intraday delivery, WAIT_CA veto, single participation,
  local-MCX commodity gate, honest data modes, position divergence, conflict
  unseated-but-visible, ceilings, routes 405/503, explain non-empty).
- tests/test_r6_live.py + tests/test_top10_research.py 18 passed.
- Combined spine regression (radar + r5 + r14 + r2b + r6 + top10) **78 passed**.
- Frontend acceptance-check 175/175.
## R2-B named activation ledger WAIT-only - 2026-08-22

```text
GET /api/v1/selection/named-activation HTTP 200 when R1/R2 hashes match
acceptanceCeiling=LIVE_NAMED_ACTIVATION_WAIT_ONLY
sourceActivationReady=false authorizedCount=0 mayConfirmCount=0
named rows = R0-B cohort; maySupportConfirmed=false
POST 405; missing source 404 R2B_SOURCE_NOT_FOUND
does not unlock CONFIRMED
test_r2b_live_named_activation.py
```

## R14 live CA join WAIT-only (R5 consumes the join) - 2026-08-21

```text
GET /api/v1/selection/ca-join HTTP 200 when R1/R2 (+R4 pin) hashes match
GET /api/v1/selection/ca-join/{symbol} 404 R14_SYMBOL_NOT_FOUND; POST 405
mismatch/missing -> 503 R14_CA_JOIN_NOT_READY (never silent last-good)
route: backend/trendforge_api/main.py
new: backend/trendforge_api/selection/r14_live.py
new: backend/tests/test_r14_live_ca_join.py
acceptanceCeiling=LIVE_CA_JOIN_WAIT_ONLY algorithmVersion=DAT-022-v1
canUnlockConfirmed=false sourceActivationReady=false executable stays absent
joinStatus NONE|JOINED|WAIT_DETAILS|CONFLICT|CANCELLED|IDENTITY_BREAK|UNKNOWN_ID|COMPANION_REJECTED
caState NONE|ADJUSTED|WAIT_CA  (this is what R5 reads)
DAT-022 via corporate_actions.reconcile_corporate_actions (reused, not rewritten):
  SPLIT den/num; BONUS den/(num+den); DIVIDEND (P-c)/P on full OHLC;
  RIGHTS TERP; MERGER/DEMERGER explicit factor + same-symbol continuity only
future CA (available_at > decision_at) hidden; hiddenFutureEventCount >= 1
UNKNOWN_ID / COMPANION_REJECTED rows: ca_state=WAIT_CA, no factor, no join
pipeline stages ... R3, R4, R14, R5 (PIPELINE_VERSION ...orchestrator-7)
R5: batch carries r14RunId/r14RunHash; hash miss -> WAIT_R5_R14_JOIN_NOT_READY
    (builder) / 503 R5_R14_JOIN_NOT_READY (GET); R5 stage BLOCKED if R14 failed
WAIT_CA rows drop structure claim_ids; confirmedCount=0; 123 jobs unchanged
test_r14_live_ca_join.py + test_r5_live_structure.py + test_r4_live_identity_pin.py
+ test_cash_post_commit_pipeline.py + test_corporate_action_integrity.py
+ test_s4s5_compare.py -> 62 passed
```

## Hybrid S4/S5 paper A/B overlay - 2026-08-21

```text
GET /api/v1/selection/s4s5-compare HTTP 200 when R1/R2 hashes match
route: backend/trendforge_api/main.py
new: backend/trendforge_api/selection/s4s5_compare.py
new: backend/tests/test_s4s5_compare.py
new: frontend/s4s5-compare.js
panel: frontend/index.html #s4s5ComparePanel
calibration=RESEARCH_PROXY_NOT_CALIBRATED
canUnlockConfirmed=false executable=false
WITH pÌ‚ = Ïƒ(-0.4 + 1.2Â·z_side + 1.2Â·z_book)
WITHOUT pÌ‚ = Ïƒ(-0.4 + 1.2Â·z_side); B4 package; B5 location
checkboxes WITH / WITHOUT / BOTH
rows stay WAIT; no CONFIRMED; Kelly illustration only
```

## R4 live identity pin - 2026-08-19

```text
GET /api/v1/selection/identity-pin HTTP 200 when R1/R2 hashes match
acceptanceCeiling=LIVE_ID_PIN_WAIT_ONLY
pkUpstreamCanVote=false pkRuntimeRequired=false canUnlockConfirmed=false
A2 hit -> PINNED; missing A2 -> UNKNOWN_ID; numeric scrip -> COMPANION_REJECTED
no membership fixtures -> PIT_UNPROVEN
r4_fixtures.py remains Q5-R4 fixture, not live R4
test_r4_live_identity_pin.py
```

## R5 live WAIT-only + IST session clock - 2026-08-19

```text
GET /api/v1/selection/structure HTTP 200
acceptanceCeiling=LIVE_WAIT_REJECT_ONLY
confirmedCount=0 canUnlockConfirmed=false
nse_index_close_eod is A5 companion, not a 123-job voter
session clock Asia/Kolkata (not UTC): PRE_OPEN / OPEN / EOD_WINDOW / CLOSED_NON_TRADING
OPEN researches last trading day; EOD after 15:35 IST may take today after dated parse
holiday/weekend keep last trading day and do not relabel it as today
test_r5_live_structure.py + scheduler IST status tests
```

## A5-C1 cash stack - 2026-08-15

```text
A5 index context; CA WAIT demotes WATCH
A6 futures-only OI; option OI unused; cash-only not penalized
C0 cash can_rank=true ceiling=WATCH; canVote=false; activation=false
B missing/junk MWPL -> MWPL_MISSING
C1 ranks WATCH only; mwpl_state=MWPL_MISSING; no CONFIRMED
A1-C1 tests 19 passed
```

## A4 PIT cash history vintages - 2026-08-15

```text
two session RAW bars + baseline complete
same date different hash -> immutable error
future CA available_at hidden from earlier decision_at
visible CA opens new adjusted series id; RAW unchanged
unresolved CA -> WAIT_CA, not bullish
can_rank=false
test_cash_a4_history.py 3 passed
```

## A3 cash-EOD WATCH discovery - 2026-08-15

```text
DISC_EOD_V1 assigns WATCH reasons from prior close + PIT percentiles
FTR-018 unused
can_rank=false
banned symbol stays REJECT with no profile
stale cash watch_count=0
test_cash_a3_discovery.py 3 passed
```

## A2 cash identity and S0/S1 - 2026-08-15

```text
NormalizedFact + instrument_id from A1 EQ rows
can_rank=false can_unlock_confirmed=false
empty ban last-good -> WAIT_RESTRICTION, public WAIT
proven ban lists RELIANCE -> REJECT RELIANCE, WAIT TCS
stale ban -> cannot REJECT
stale cash -> quality_state=STALE, S0 WAIT
test_cash_a2_identity.py 5 passed
```

## A1 cash last-good staging - 2026-08-15

```text
stage_cash_bytes persists SourceResult + 2 EQ staging rows
can_support_confirmed=false
stateCeiling=WAIT
no NormalizedFact / instrumentId
empty parse -> PARSE_FAILED, 0 rows
missing last-good -> NOT_ATTEMPTED
test_cash_a1_staging.py 3 passed
```

A2 identity / NormalizedFact not started.

## R1 persisted selection runs - 2026-08-15

```text
POST /api/v1/selection/live/refresh persists WAIT batch
GET /api/v1/selection/live returns latest stored run
second persist sets comparableBaseline=COMPARED
liveConfirmedCount=0
test_r1_live_decision.py 8 passed
```

## R0-B shared NSE breaker proven; MWPL stays confirm-ineligible - 2026-08-22

```text
GET /api/source-inventory/r0b-cohort
  reviewedCount=6
  provenCount=5  (cash, ban, FO, index, CA)
  nse_mwpl_percentages proven=false confirmEligible=false
  canVote=false  sourceActivationReady=false  gateAuthorized=0
Shared runtime proof (not per-source unique):
  rate_budget SHARED_NSE_DOMAIN_CAP
  retry_policy SHARED_HTTP_RETRY max_attempts=3
  circuit_breaker_policy SHARED_NSE_DOMAIN_BREAKER fail=3 cooldown=900s
  retention_policy SHARED_MARKET_DATA_STORE detailed_trading_days=5
Activation draft (NOT executed):
  docs/fable/remaining_build/FILE_A_R2B_ACTIVATION_AMENDMENT_DRAFT.md
```

## R0-B field-by-field review - 2026-08-15

```text
GET /api/source-inventory/r0b-cohort
  reviewedCount=6
  provenCount=0
  quarantinedCount=6
  canVote=false
  sourceActivationReady=false
  gateAuthorized=0
nse_fno_ban compiled fields include timezone=Asia/Kolkata and
schema_version=nse_fo_secban_csv_v1
rate_budget / retry / circuit_breaker remain missing/waived
publication_calendar is NSE_FO_TRADING_DAYS, not catalog "daily"
```

## R0-B first source cohort - 2026-08-15

```text
GET /api/source-inventory/r0b-cohort
  slice=R0-B
  sourceActivationReady=false
  gateAuthorizedSourceKeyCount=0
  provenCount=0
  quarantinedCount=6
  members: nse_fno_ban, nse_mwpl_percentages, nse_bhavcopy_eod,
           nse_fo_bhavcopy, nse_index_close_eod, nse_corporate_filings_actions
```

File A Â§25.20.1 records R0-A (compiler honesty) / R0-B (this cohort) /
R0-C (remaining inventory quarantined). R2 is not started.

> **Superseded later the same day:** the live selection surface is no longer
> on-demand-only. See **R1 persisted selection runs** above â€”
> `POST /api/v1/selection/live/refresh` stores WAIT runs; GET returns the
> latest stored run when present.

## R1 live decision DTO - 2026-08-15

```text
Independent compiler recheck: H1A0 6/6; pin matches file SHA f1abcdceâ€¦
GET /api/v1/selection/live
  acceptanceCeiling=NO_LIVE_CONFIRMED
  liveConfirmedCount=0
  sourceActivationReady=false
  no quantity field
STA-006 WATCH->CONFIRMED denied to WAIT
CROSS-020 adjusted series id != raw series id
PYTHONPATH=backend pytest
  test_r1_live_decision.py + Q5 family/selection/structure/enrichment
  71 passed
frontend npm test
  159/159
```

R1 is started, not finished. Full EvidenceClaim envelope on every live
voting claim, comparable-run diffs with a real prior run, and CROSS-020
storage of adjusted bars remain open. No live CONFIRMED. No R2 activation.

**2026-08-16:** Remaining File A R1 is the alias-aware live evidence DTO /
why-not-confirmed bundle. Remaining R2 is attention order over existing
A1â€“C1, not a new S0â€“S3. The Inventory Workbench / Source Operations page
does **not** display those objects. Collector last-good counts are not
stock evidence. R3â€“R15 were plan-debugged before wiring: `resolve_evidence`
is fixture-only; post-commit does not call it; R15 is not the workbench.
See locked plan Â§12 and D-035.

> **Later the same day:** STO persistence + refresh landed (see **R1 persisted
> selection runs** at top). Frontend acceptance is now **161/161**. The 159
> figure above is the earlier live-DTO-only baseline.

## H1A0 6/6 re-pin - 2026-08-15

```text
REVIEWED_WORKBOOK_SHA256
  f1abcdce2b451b4ded9d9e9c8eb6bd63fae82853803f60bef60a1651dd52eb0b
compile_default_inventory()
  ok=true
  H1A0=6/6
  stale_resolution=0
  invalid_resolution=0
  unexplained_overlap=0
  rows=409 endpoints=387 contracts=354
  overlap_records=32
  SAME_DATASET_ALIAS=7 PARENT_CHILD=20 DISTINCT_SHARED_ENDPOINT=5
  sourceActivationReady=false
  gateAuthorized=0
  living_map live=176 vs CROSS-002 pin 129 (not rebuilt)
CROSS-001-v2 dispositions:
  bulk.csv -> SAME_DATASET_ALIAS nse_bulk_deals_today_csv
  AMFI directory -> DISTINCT_SHARED_ENDPOINT
  MCX delivery page -> DISTINCT_SHARED_ENDPOINT
PYTHONPATH=backend pytest backend/tests/test_r0_residual_slice.py
  plus test_default_compiler_reads_workbook_when_present
  PASS after pin
frontend npm test
  157/157
```

H1A0-04 now passes because the 3 new groups have reviewed exact-key
dispositions and the pin matches the current workbook. CROSS-002 is still
the 2026-07-23 129-key review and is allowed to show drift. Activation
stays false. R1 is unblocked only for planning; product R1 coding starts
only after the operator chooses it.

## Auditor upgrade - 2026-08-15

```text
PYTHONPATH=backend pytest backend/tests/test_r0_residual_slice.py \
  backend/tests/test_intraday_stock_details.py \
  backend/tests/test_market_activity.py::test_ranker_builds_watch_not_ready_from_confluent_activity \
  backend/tests/test_market_activity.py::test_stale_sources_cannot_create_activity_watch \
  backend/tests/test_market_activity.py::test_market_activity_api_fetches_persists_and_returns_research_watch
17 passed
cd frontend; npm test
157/157 passed
GET http://127.0.0.1:8000/api/source-inventory/compiler-report
  ok=true; H1A0=5/6; sourceActivationReady=false; gateAuthorized=0
  workbookSha256=f1abcdce2b451b4ded9d9e9c8eb6bd63fae82853803f60bef60a1651dd52eb0b
  stale_resolution=29; unexplained_overlap=32; rows=409; endpoints=387; contracts=354
  maturityStageCounts REGISTERED=409, all later rungs 0
GET http://127.0.0.1:8000/
  sourceHealthLadder and maturityLadder mounts present
GET http://127.0.0.1:8000/api/source-health
  132 rows; sample GREEN/REGISTERED; gatePermission=false; sourceActivationReady=false
identity-only compile: stale_resolution=0; unexplained_overlap=3
Do not re-pin. New unexplained groups:
  https://archives.nseindia.com/content/equities/bulk.csv
  https://www.amfiindia.com/online-center/portfolio-disclosure
  https://www.mcxindia.com/market-operations/clearing-settlement/delivery-reports
```

CROSS-014: `detail_score` and `activity_score` cannot set WATCH_LONG/WATCH_SHORT.
TDG-GAP-001: zero inferred catalog proofs; 15 fields stay missing.
CROSS-007: 29 old identities still match; pin not refreshed because 3 new
overlaps exist. CROSS-006: ladder mounts on Source Health and Live Ops.
No click-through browser tool was available; ladder mounts were verified
from the live HTML and compiler-report JSON. R1 is blocked until strict
H1A0 returns 6/6.

## R0 residual slice - 2026-08-15 (superseded)

Earlier same-day notes claimed a 9-test residual slice and still described
inferred TDG proofs. The auditor upgrade section above replaces those claims.

## Bundled Inventory Workbench acceptance - 2026-08-14

```text
node --check product-fixture.js + 10 copied JS modules        PASS
node tests/q5-contract.test.js                                PASS
node tests/acceptance-check.js                                154/154 PASS
node tests/inventory-workbench.test.js                        24/24 copied files PASS
pytest live panels + FII signals + manual refresh             21/21 PASS
full backend baseline                                         803 PASS / 20 FAIL
Playwright desktop drawer (1538x698)                        OBSERVED: 1461x670px (95.0% x 96.1%)
Playwright 390x844 full-screen drawer                         OBSERVED
```

| Claim | Observed evidence | Ceiling |
|---|---|---|
| Independent static runtime | `/inventory-workbench/` returned the copied 19,699-byte app; no port 5500/8080 service is required | TrendForge server still owns live API overlays |
| Real catalog data | Browser parsed and rendered 165 cards / 129 unique keys from copied `links_105.json` | Catalog/sample visibility is not gate authorization |
| Live panels | `/api/panels/live` returned contract `trendforge.livePanels.v1`; inventory rendered current/saved labels | Missing/stale rows remain labelled and cannot confirm |
| FII strip | `/api/institutional/fii-stock-signals` returned 349 large deals / 462 holding-reference rows | Large deals are not certified FII; name-only identity stays explicit |
| Snapshot integrity | Manifest contains 24 allow-listed files and copied hashes equal source hashes | Source app remains frozen and unchanged |
| Responsive design | Host-owned iframe drawer observed at desktop `95vw x 96vh` with `top:2vh`; final mobile rule produced `100vw x 100dvh` at 390x844 | Embedded app retains its own design system |

Primary hashes:

```text
frontend/index.html                                           CC0AE9389FE39FE9DC3590F0EF0E521F9C0DC9AF7B2DB2B0D9F33B12DFFA641E
frontend/product-fixture.js                                  4D1E0C17D09DAEC37A0F485601C5BF4CEF2E75D211C246DBBA10269955D5052F
frontend/theme-final.css                                     9404A9B85A979A8D19BD7CF31E2A19F7BE7CD33D9607FA18E1DF62563E9F319D
inventory-workbench.manifest.json                            F684981E8F9449DD09EBC58C20DB23D2F22D4748FD0533BBB8C441AC9082078A
```

The full backend failures predate and do not touch this static integration, but
they remain open project risk and prevent a clean project-wide verdict. HTTP
200 alone was not counted as success: browser parsing, rendered records,
contract fields and focused API tests were also observed.
## Runtime frontend shell alignment - 2026-08-14

```text
cd D:\TrendForge\frontend
node --check app.js                         PASS
node --check q5-contract.js                 PASS
node tests/q5-contract.test.js              PASS
node tests/acceptance-check.js              151/151 PASS
getElementById IDs missing from HTML        0
```

| Claim | Ceiling |
|---|---|
| Visual chrome matches FINAL_PRODUCT rooms | Layout only. Fixture numbers not loaded. |
| All Stocks board | Live `/api/radar` rows + filters. MCX empty = Context Only. Not R15 DTO. |
| Tool rooms (14) | `WAIT_DTO_UNAVAILABLE` / activation / chain ceilings. No invented OI/IV/GEX. |
| Journal quantity | Forced 0. Not an order ticket. |
| Public state chips | Four Q5 states. Lock is `lockBadge`, not `selectedState`. |
| File A R15 Scanner Lab | **OPEN**. This is a presentation seam only. |

Browser desktop/mobile exercise of the new shell was not automated in this
run. Re-open `http://127.0.0.1:8000/` after restarting the API if the process
is still serving a cached older `index.html`.

## Static research-terminal product preview - 2026-08-14

```text
JavaScript parse / new Function             PASS
Required feature-contract anchors           PASS
HTML duplicate IDs                          0
HTML IDs / buttons / sections               55 / 56 / 9
Rendered desktop file preview                OBSERVED - user confirmed correct load
Automated desktop/mobile Playwright QA       PENDING - local file/server unavailable to automation browser
```

| Preview surface | Observed contract | Verification ceiling |
|---|---|---|
| Operations header | Research-only mode, history date, timeframe, refresh, activity metrics, newer-snapshot notice and Lightning strip | Fixture interaction only; not a live scheduler or market clock |
| All Stocks | Eight fixture instruments, table/cards, search, mode/direction/state filters, sort and inspect actions | Static FMR-009/R15 design target; runtime DTO integration remains open |
| Decision cards | Side-by-side research candidates, green/red direction rails, states, geometry, evidence components and rationale | Evidence direction only; no order, quantity or advisory authority |
| Structure Lab | Elliott primary/alternate counts plus harmonic XABCD/PRZ geometry and invalidation | One correlated `STRUCTURE` family; closed-bar fixture only |
| Stock Evidence | Decision, Chart & Structure, History & Replay, Options/Gamma, Source Lineage, PKScreener and Model Lab tabs | Replay/model/derivatives values remain fixture or locked where unproved |
| Inventory drawer | Same-origin `frontend/inventory-workbench/` served at `/inventory-workbench/`; desktop host shell is `95vw x 96vh`, mobile is full-screen | Read-only glass; **not** R1 live stock evidence; **not** R2 ranking |

The artifact remains a static fixture. Elliott counts, historical replay,
research geometry and Model Lab values do not represent production backend
evidence. Model authority, probability UI, executable quantity and execution
remain disabled. The observed desktop load does not close R15, R16 or R18 and
does not prove responsive/browser regression coverage.

## FII four-card acceptance - 2026-08-13

| Source key | State | Data date | Normalized rows | UI role |
|---|---|---:|---:|---|
| `screener_in_fii_holding_change` | `SUCCESS_NEW` | 2026-08-13 | 105 | `THIRD_PARTY` INFO |
| `tickertape_fii_holding_change_3m` | `SUCCESS_NEW` | 2026-08-13 | 300 | `THIRD_PARTY` INFO |
| `dhan_fii_holding_change` | `SUCCESS_NEW` | 2026-08-13 | 32 | `THIRD_PARTY` INFO |
| `equitymaster_fii_buys_reference` | `SUCCESS_NEW` | 2026-08-13 | 25 | `THIRD_PARTY` INFO |

Observed API: 349 large deals, 462 holding/reference rows, 351 resolved
symbols, latest saved fetch `2026-08-13T15:48:49.622928Z`. Catalog observation:
165 rows, 129 logical keys, 122 primaries; all four cards were populated and
rendered. Focused backend tests: **14 passed**. FII panel and catalog Node tests:
**passed**. Missing identity stays `NAME ONLY`; missing Dhan holding level stays
null. No consensus vote or screener score formula changed. The inventory SPA
renders the strip; the TrendForge command-room frontend does not (`TF-APP-FII-M1`).

## Official BSE/RBI and calculated-output acceptance - 2026-08-11

Observed production persistence:

| Key | State | Data date | Normalized rows |
|---|---|---:|---:|
| `bse_financial_results_xbrl` | `SUCCESS_NEW` | 2026-08-10 | 5,126 |
| `bse_shareholding_pattern` | `SUCCESS_NEW` | 2026-08-10 | 5,508 |
| `rbi_tbill_yield` | `SUCCESS_NEW` | 2026-08-05 | 3 |
| `industry_peer_group_v1` | `CALCULATED_INFORMATIONAL` | 2026-08-06 | 500 |
| `pcr_max_pain_history_v1` | `CALCULATED_INFORMATIONAL` | 2026-08-10 | 1 |
| `option_greeks_calculated_v1` | `CALCULATED_INFORMATIONAL` | 2026-08-10 | 65 |

The BSE rows are explicitly `FILING_INDEX_XBRL_DISCOVERY`. They prove dated
filing discovery, not statement facts or ownership percentages. Therefore
`fundamental_ratios_v1` emits no production rows until a bounded second-stage
iXBRL fact parser preserves context and dimensions. No missing fact is invented.

Acceptance evidence:

```text
focused source/registry/scheduler              66 passed
final matrix/source/calculation slice           52 passed
targeted Ruff                                   all checks passed
Python compileall                              passed
Inventory Node suites                          13 passed / 0 failed
catalog                                        161 rows / 125 logical keys
registry representation                        119 / 119
panel registration grep                        NO_PANEL_REGISTRATION
```

The full backend run produced **784 passed / 21 failed** before the one stale
Pack-7 count assertion was corrected. The other failures are outside this
milestone (older endpoint/timeout fixtures, missing async plugin, IV-rank work,
source-inventory workbook/hash drift, Upstox parser work and VYOM fixtures).
They are not counted as acceptance and were not hidden or weakened.

## Files 1-3 cross-pack audit - 2026-08-11

- Exact audit:
  `docs/fable/evidence/FILE1_2_3_INTEGRATION_AUDIT_20260811.md`.
- Production-family coverage: file 1 = 7/8, file 2 = 4/6, file 3 = 7/10;
  total = 18/24. Every covered family has positive-row last-good data.
- Registry compiler: 112 contracts / 112 unique, 0 activation-ready and all
  schedule authorities provisional. Registry SHA-256 is
  `95B67C66279C04D96C4CB16E766AC30BD0BDA51FC08E9FFD8B34BBB5B2F327C5`.
- Catalog merge: 154 rows / 118 logical keys; all 112 registry keys represented.
- All 13 Inventory Node suites passed, including Consensus/Nifty outputs,
  Screener financial score invariance, gap feeds, catalog merge and live panels.
- Three obsolete fixture assertions were repaired: the old 112-card ceiling,
  the old two-row PIT sample, and the pre-2026-08-06 Consensus file hash. The
  tests remain strict against the current approved artifacts.

## Pack 7 validation - 2026-08-11

- Full input read: `C:\Users\sakth\Downloads\7.txt`, 2,019/2,019 lines.
- Terminal ledger:
  `docs/fable/evidence/pack7-20260811/PACK7_SOURCE_RECONCILIATION.json`.
- Exactly 17 candidates are classified; every reuse key exists in the typed
  registry and no broker/scraper placeholder key was added.
- The existing option parser test proves Max Pain is derived from official OI
  while delta/gamma and other missing Greeks are not invented.
- Pack-7/Pack-6/parser/registry/service acceptance: **58 passed** using an
  explicit writable pytest base; targeted Ruff: **all checks passed**.
- A first root-launched pytest command failed import collection and a second
  run hit the host temp-directory ACL. Both were launch-environment failures;
  the corrected backend run above is green and no test was weakened.

## Pack 6 validation - 2026-08-11

- Full input read: `C:\Users\sakth\Downloads\6.txt`, 1,957/1,957 lines.
- Terminal ledger:
  `docs/fable/evidence/pack6-20260811/PACK6_SOURCE_RECONCILIATION.json`.
- Live MD69 attempts 1531-1534 are `PARSED_STRUCTURED`, data date 2026-08-10,
  with 18/6/113/84 normalized rows.
- Regression covers the observed NSE v3 contract shape where CE omitted symbol
  and expiry but the request URL carried both values.
- A contract with no recoverable identity is `WAIT_SCHEMA_MISMATCH`, not a
  blank-symbol row.
- Pack-6/parser/registry/service acceptance: 54 passed; targeted Ruff passed.
- An earlier broader mixed run also exposed two stale NSE session-seed fixture
  assumptions and one sandbox read-only DB write. Those unrelated failures were
  not counted as Pack 6 acceptance and no unrelated test was weakened.

## 2026-08-11 - Pack 5 acceptance

- Pack-5/parser/service/registry/intraday set: **64 passed**.
- Pack-5 golden parser/retention file: **14 passed**.
- Targeted Ruff on changed backend files: **all checks passed**.
- Inventory `node tests\\catalog_registry_merge.test.js`: **passed** for 154
  cards, 118 logical keys and all 112 registry keys represented.
- Live read-back: attempts 1524, 1525 and 1526 exist in
  `market_data_latest`; their object files are readable and populated.
- Failure observation: the old NSE market-status validator rejected an
  auxiliary index row and archived zero bytes as NEW. Tests reproduced both
  defects; the repaired route archived 2,101 bytes and parsed five valid
  session rows. Empty/failed refresh retains last-good.
- No Consensus or Screener formula file was edited.
## 2026-08-06 - Dynamic manual/scheduled panel handoff validation

Verdict: **VERIFIED FOR THE RUNNING LOCAL SESSION**.

```text
Refresh button             69 attempted / 67 populated / 2 valid-empty / 0 failed
committed manifest         manual-20260806-144047
canonical projection       67 sources / 7,284 overlay records / 2,198,752 bytes
late scheduler audit       newer MISSED manifest skipped; last usable manifest retained
Sector                     38/38 tracked sectors
Consensus                  8 active boards / 60 symbols
Nifty Filter               3 BUY / 3 SELL
Screener                    200 visible / 2,867 extracted symbols
focused backend            55 passed
frontend                    4 suites passed
browser after final reload populated; no new console error
```

The observed panel state was `STALE` because `nse_all_indices` was 364 seconds
old when checked, correctly exceeding the 300-second LIVE gate. It remained
visible with its original 14:42:12 IST fetch time. The next scheduled download
or manual Refresh can make the panels LIVE only when every required critical
source satisfies the same date and age rules.

## 2026-08-06 - Saved panel overlay repair validation

Verdict: **VERIFIED WITH UNRELATED FULL-SUITE CAVEATS**.

```text
API refresh state        CANONICAL_MANIFEST
diagnostics / overlays   18 / 11
Sector                   38/38 tracked sectors
Consensus                8 active boards / 61 symbols
Nifty Filter             3 BUY / 4 SELL
Screener                  200 visible / 458 matching
browser console          clean
focused backend          52 passed
frontend                 4 suites passed
full backend             626 passed / 25 unrelated failures
```

The displayed panel state was honestly `STALE` because source age exceeded
300 seconds; saved records and their original fetch timestamps remained visible.

## 2026-08-06 - Corrected full MD69 refresh

Observed through the local API after loading the repaired process:

```text
69 attempted   67 populated   2 VALID_EMPTY   0 FAILED
manifest       data/market_data/2026-08-06/snapshots/manual-20260806-140044/manifest.json
```

The valid-empty results were `nse_daily_buyback` and `nse_pit_symbol`, which
returned successful responses with no current records. All other 67 sources
produced populated normalized records.

## 2026-08-06 - MD69 remaining-source repair validation

Verdict: **VERIFIED WITH RESEARCH-SOURCE CAVEATS**.

```text
seven-contract MarketDataService canary     7/7 SUCCESS_NEW / PARSED_STRUCTURED
focused and broader source tests            66 passed / 61 deselected
Ruff changed-file check                     PASS
Python compileall                           PASS
```

Observed source rows: SLB 277; CFTC Legacy 12; CFTC TFF 9; combined CFTC 32;
NSE Large Deals 357; AMFI 440; NSDL 48. The canary used the real acquisition
and normalization path with the MD69 store disabled. The existing endpoint
client archived raw endpoint payloads; it did not commit a new MD69 manifest or
latest pointer. Full evidence and caveats are in
`docs/fable/MD69_REMAINING_SOURCE_REPAIRS_2026-08-06.md`.

## 2026-08-05 - MD69 documentation truth check

The current operation reference is
`docs/fable/MD69_REFRESH_OPERATION_REFERENCE.md`. It is based on a repeated
38-pass focused backend run, all 11 inventory-app Node suites, the local API
status response, rendered localhost UI and observed scheduled-task state.
A real manual all-69 run was observed after that earlier test pass; its actual
mixed result is recorded below. No document claims that all 69 sources
populated successfully or that the resulting closed-market data is LIVE.

## 2026-08-05 - Manual Refresh and Last-Saved Data

Verdict: **VERIFIED WITH LIVE-SOURCE AVAILABILITY CAVEATS**.

```text
collector status: COMPLETED / 69 dynamic registry sources
schedule: 09:00, 09:17, 10:30, 12:30, 13:30, 15:00 IST
automatic task: enabled and RUNNING
manual run: 69 attempted / 54 successful / 2 valid-empty / 13 failed
panel API: MARKET_CLOSED / CACHE_RESEARCH / 10 saved overlays
saved bhavcopy: 2,416 source rows / 2,122 normalized rows / data 2026-08-05
focused backend: 38 passed
wider relevant backend: 149 passed, 1 unrelated Parquet 503
frontend: 11/11 Node scripts passed
```

Fixture tests prove all-registry manual execution, lease protection, closed
session execution, timestamp preservation, last-good fallback, and stale saved
panel calculation. The actual manual run committed
`manual-20260805-213316`; the rendered localhost UI then showed the 38-sector
pulse, 6 active Consensus boards / 50 symbols, and 200 Screener rows. All
three badges were correctly red `MARKET CLOSED`; no browser console error was
observed.

## 2026-08-05 - Closed-Session Current-Data Bridge Repair

Verdict: **VERIFIED WITH SOURCE-AVAILABILITY CAVEATS**.

Observed through the running API and browser:

```text
API session: MARKET_CLOSED
refresh state: CANONICAL_MANIFEST
current overlays: nse_bhavcopy_eod 2416, nse_large_deals 152,
                  nse_trade_to_trade 431, nse_pr_market_snapshot projected
screener badge: Data 2026-08-05 / Fetched 05 Aug 2026 18:48:00 IST
BAJFINANCE browser: 1158.80 / +0.85%
BAJFINANCE object: close 1158.80 / previousClose 1149.00 / 2026-08-05
browser console errors: 0
focused backend: 18 passed
frontend: 10/10 Node scripts passed
full backend: 608 passed, 24 failed, 2 warnings
```

The full-suite failures are outside this repair and include read-only workspace
writes, missing async pytest support, and pre-existing contract/hash drift. The
focused repair tests pass. `nse_all_indices`, variations, volume and most-active
P0 sources were not collected on 2026-08-05; therefore Sector is unavailable
and Consensus has no current voting boards. The repair intentionally blocks
their old catalog samples instead of relabelling them current.

## 2026-08-05 - MD69-M7 Production Activation

Verdict: **VERIFIED WITH PROVISIONAL-SCHEDULE CAVEAT**.

Observed:

```text
backup integrity: ok
backup SHA-256: B9EFD9B74372A0F5F3C932032DB8A632AC2436657AEC7FFF2646EF2B7EB3E757
production DB integrity after migrations: ok
task: TrendForge MD69 Collector / Running / IgnoreNew
first persisted latest sources: 8
focused M1-M7 regression: 90 passed, 1 warning
20-second retry observation: attempts/runs/manifests unchanged
```

The task launched the intended hidden PowerShell wrapper and one logical Python
collector (Windows venv launcher plus child interpreter). The initial run
persisted current-day BSE/NSE bhavcopy, T2T and PR data plus four available
previous-day EOD datasets. Failed and stale sources did not stop successful
sources.

An initial wrapper exit was traced to PowerShell treating a normal source
warning on stderr as fatal; the wrapper now logs such warnings without killing
the collector. An extra foreground diagnostic process was identified and
terminated, leaving only the scheduled-task collector.

Automatic collection is real, but timing authority remains `PROVISIONAL` and
readiness remains false. This activation does not claim official publication
cadences or universal 69/69 live success.

## 2026-08-05 - MD69-M6 Campaign Verification

Verdict: **VERIFIED WITH CAVEATS** at the no-network fixture ceiling.

```text
no-network dry-run tests: 2 passed
focused M1-M6: 89 passed, 1 warning
full backend: 622 passed, 8 failed, 2 warnings
frontend: 10 Node test scripts passed
Ruff: All checks passed
Python compilation: PASS
```

Observed dry run: `FIXTURE_ONLY_NO_NETWORK`; 69 registry sources; 25 due; 25
completed; 69 unique manifest entries; 69 health rows; provisional authority;
activation false. `requests` and `httpx` were patched to raise in the test.

Evidence:

```text
docs/fable/evidence/md69-m6-20260805/dry_run_report.json
SHA-256 748DB2E736ABB7323491587DB3382A1D768A4C2AA147C1AA36CB6D8A4F572E2C

docs/fable/evidence/md69-m6-20260805/market_data/2026-08-05/snapshots/0917/manifest.json
SHA-256 0817CCC5F33BE2E2F1062518A795F184C1F18F3A6D9C9B03B227AF55B901F467
```

Full-suite failures: corporate-disclosure registration expectation;
`test_derivatives_fanout` async plugin absence; three old NSE seed/route
expectations; and three workbook/source-map digest/review expectations. These
are outside the MD69 implementation files and belong to the same pre-MD69
families recorded when 24 failures were observed. No focused MD69 failure was
present.

Protected frontend hashes:

```text
consensus.js FADD34BA723AA72562D18ACF77629E01415834FCC6F2A24DA594FD2672BABDA4
screener.js  DA72C82800E8E465D4130DA180265B581650AE4DBB04CE604D12DEE10A989F2A
links_105.json 668C0E026E43012C91B8B6176B1D642091C805E34CB779343D2274D447283025
```

At the M6 checkpoint, M7 was not verified or activated. Official cadence evidence and separate
production migration/service approval remain required.

Post-suite safety inspection: the existing full test suite touched the
production research DB file's mtime. Read-only SQLite inspection showed no
`0020_market_data_69_store` or `0021_market_data_69_scheduler` migration and no
MD69 attempt/last-good/manifest/lease/schedule/run tables. No Python/uvicorn
collector process was running.

## 2026-08-05 - MD69-M5 Canonical Panel Bridge

Verdict: **VERIFIED** at the temporary canonical-manifest ceiling.

```text
alignment + live-panel tests: 17 passed
combined MD69 M1-M5 backend tests: 87 passed, 1 warning
frontend Node suites: 10 passed
Ruff: All checks passed
Python compilation: PASS
```

Observed: timestamp/hash lineage, maximum-skew calculation, wrong-day/future/
missing rejection, read-only SQLite access, manifest/object hash validation,
catalog-copy isolation, zero legacy-client construction in canonical mode, and
fail-closed canonical provider errors. Protected frontend hashes remained:

```text
consensus.js FADD34BA723AA72562D18ACF77629E01415834FCC6F2A24DA594FD2672BABDA4
screener.js  DA72C82800E8E465D4130DA180265B581650AE4DBB04CE604D12DEE10A989F2A
```

This does not establish live source usability or authorize production
migration/background activation.

## 2026-08-05 - MD69-M4 Scheduler and CLI

Verdict: **VERIFIED** at the mocked/temporary ceiling.

```text
scheduler and CLI tests: 14 passed
combined registry/store/service/scheduler/calendar/live-panel: 80 passed, 1 warning
Ruff: All checks passed
Python compileall: PASS
```

Observed: exact six IST slots and fixed +05:30 offset; due-only service subset;
69 manifest entries; disabled/provisional zero-call gates; holiday eligibility;
late audit isolation; restart miss recovery; lease collision/expiry; 15:35 EOD
per-source completion; 69-row health; seven CLI routes. All DB paths were temp.

Publication schedules remain provisional, so the foreground collector returns
`ACTIVATION_BLOCKED` unless a test explicitly enables fixture policy.

## 2026-08-05 - MD69-M3 Acquisition Service

Verdict: **VERIFIED** at the injected-transport ceiling.

```text
service tests: 19 passed
combined registry/store/service/source/parser/adapter tests: 82 passed, 1 warning
Ruff: All checks passed
Python compileall: PASS
```

Observed: 69/69 normalizer support; required parameter fan-out; PR response
reuse; derivatives session sharing without response reuse; global/domain caps;
queued circuit opening after two failures; independent failure isolation;
contract-specific valid-empty states; poisoned/future rows quarantined; failed
refresh retained the prior last-good pointer.

This milestone made no live market request and does not establish live source
usability. Live scheduling and production activation remain separate.

## 2026-08-05 - MD69-M2 Storage and Retention

Verdict: **VERIFIED** at the temporary-storage ceiling.

Observed claims:

1. Identical bytes on different trading days produce one SHA-256 object and a
   later `SUCCESS_UNCHANGED` attempt.
2. Failed attempts leave the last-good pointer unchanged.
3. A 69-entry unique-source manifest is written atomically; replace failure and
   database failure both preserve the prior committed file.
4. The additive migration was applied only to temporary test databases.
5. Dry-run is the retention default. Execution preserves the current date,
   newest five completed trading dates, last-good objects, and all paths beyond
   the configured root. Nested symlink/reparse content is rejected.

```text
cd D:\TrendForge\backend
..\.venv\Scripts\python.exe -m pytest tests\test_market_data_store.py -q
13 passed

..\.venv\Scripts\python.exe -m pytest tests\test_market_data_store.py \
  tests\test_market_data_registry.py tests\test_source_runtime_hardening.py \
  tests\test_exchange_calendar.py tests\test_live_panels.py -q
47 passed, 1 warning

..\.venv\Scripts\ruff.exe check trendforge_api\market_data_store.py \
  tests\test_market_data_store.py --no-cache
All checks passed
```

This does not verify live acquisition, due scheduling, production migration,
or service activation. Those remain later MD69 milestones.

## 2026-08-05 - MD69-M1 Registry and Executable Adapter Matrix

Verdict: **VERIFIED WITH CAVEATS** at the M1 contract ceiling.

Verified observations:

1. The runtime CSV is byte-identical to the approved 69-row source and matches
   SHA-256 `416C670181E2F2BAB685C9314E3B8D1CC7A4B707413E3E680F8E153B91814FEC`.
2. It contains exactly 69 rows and 69 unique keys; its sorted key-set hash is
   `2ADA6FA789999FADB737F77C0ECFD948A8B884D593E2EC6607F678CBA224C6B1`
   and matches the current 69 primary inventory feeds.
3. All 69 profiles resolve to an existing endpoint or monitor descriptor and
   an existing structured parser or adapter callable.
4. Required parameters are covered by explicit providers or fan-out strategies.
5. Physical response reuse is distinct from session sharing. NSE PR ZIP rows
   use response reuse; derivatives/variation/most-active pools use session
   sharing; the F&O bhavcopy/participant-OI label is not treated as one response.
6. All schedule evidence is provisional, activation is false, and complex
   human cadence text is retained rather than guessed into runnable timing.
7. Network entry points were patched to raise during compilation; all registry
   tests still passed, proving M1 performs zero network calls.

Observed commands and results:

```text
cd D:\TrendForge\backend
..\.venv\Scripts\python.exe -m pytest tests\test_market_data_registry.py -q
13 passed in 1.83s

..\.venv\Scripts\python.exe -m pytest \
  tests\test_market_data_registry.py \
  tests\test_source_runtime_hardening.py \
  tests\test_exchange_calendar.py tests\test_live_panels.py -q
34 passed, 1 warning in 5.30s

..\.venv\Scripts\ruff.exe check \
  trendforge_api\market_data_registry.py tests\test_market_data_registry.py --no-cache
All checks passed

cmd /c npm test
135/135 checks passed

..\.venv\Scripts\python.exe -m pytest tests -q
551 passed, 24 failed, 2 warnings in 114.79s
```

Full-suite caveat: the same 24 previously observed failures remain outside M1:
parquet/SQLite/report writes blocked by the execution sandbox, one async test
without `pytest-asyncio`, older NSE seed and BSE timeout expectations, and
existing workbook/source-map hash drift. The focused M1 and surrounding-source
suites are clean.

This does not verify publication cadence, live source usability, scheduler
behavior, database migration, retention, or panel freshness. Those remain later
approval-gated milestones.

## 2026-08-04 - Seven Inventory Gap Feeds

Verdict: **VERIFIED** for fetch/archive/normalize/export scope, with source
activation still false.

Observed evidence:

```text
production export: all_gap_feeds_populated=true
data date: PR/bhav/T2T 2026-08-03; API/reference feeds 2026-08-04
normalized: bhav 2415; T2T 447; lots 247; board 20; futures 36;
            options 133; IPO 4; PR 2434
Python syntax: 117 files valid
focused backend parser tests: 6 passed
```

Fixtures prove all six T2T series, Kite integrity/filter/aggregation,
volume/value most-active merging and section split, unchanged IPO status,
symbol-safe PR rows, and catalog/resolver registration. HTTP 200 alone is not
accepted; every released feed has populated structured records.

## 2026-07-29 - Grok Residual Governance Closure Validation

Verdict: **VERIFIED** for the three requested governance corrections.

Observed assertions:

1. Safe prohibition `Do not pick next milestone M10` is accepted.
2. Unsafe `Pick next milestone M10 now` and the other next-M action forms are
   rejected, including when safe and unsafe text are mixed.
3. README, Discovery and Options each expose the same File A selector vocabulary:
   `R0-R18`, `CROSS-###`, or `TDG-GAP-###`; `M/T/PK` are subordinate.
4. The Discovery machine owner table remains R-owned and structurally validated;
   CROSS/TDG are File A work selectors, not replacement M/T/PK owners.
5. `Q4W-006` now states the complete R15/R16/R18 `FMR-011` role split.
6. FMR maps, decision IDs, coverage rows and changed-file containment remain
   unchanged and valid.

```text
focused governance tests: 25 passed in 0.31s
coverage: 155 rows; added=[]; removed=[]; changed=[]
decisions: count=29; max=D-029; duplicates=[]
backend: 534 passed in 101.42s
frontend: 135/135 checks passed
runtime baseline: 643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D
```

This is governance verification only and makes no production-readiness, source
activation, scanner-performance, probability, quantity or execution claim.
## 2026-07-29 - Residual Single-Spine Adversarial Verification

Scope: File A/FMR role wording, Discovery and Options detail-catalog purity,
remaining-build navigation, governance validator/tests and traceability. Runtime
business logic was explicitly out of scope.

Observed structural assertions:

1. `FMR-011` remains mapped to `R15`, `R16`, `R18` and its role split is
   consistent across File A, Final Merge and README.
2. File A section 25.21 is the canonical FMR map; Final Merge, README and all
   FMR coverage rows normalize to the same owner/link sets.
3. Discovery contains exactly one machine row for each of 33 `M0-M23`, `T0-T4`
   and `PK-A..PK-D` tags. R owners are restricted to `R0-R18`; FMR references
   are restricted to `FMR-001..011`; each row's R owners are covered by the
   union of its FMR owners.
4. Missing tags, duplicate tags, invalid R owners, invalid FMR references and
   FMR owner-coverage disagreement fail closed.
5. `Start Phase T0`, `Start with Phase T0`, numbered Sprint tables, global M
   arrows, `PK-A only` and `Prefer this file` fail schedule validation. Mixed
   safe and unsafe text still fails.
6. Permanent `sourceActivationReady=false` law fails; conditional wording tied
   to the current observed runtime state passes.
7. Decision inventory reports 29 IDs, maximum `D-029`, and no duplicates.
8. Governance changed-file validation requires both the exact allowlist and a
   matching pre-edit runtime manifest hash.

Observed commands and results:

```text
python -m py_compile docs\fable\remaining_build\build_coverage_csv.py
PASS

python -m pytest -q docs\fable\remaining_build\test_build_coverage_csv.py
................... [100%]
19 passed in 0.33s

python docs\fable\remaining_build\build_coverage_csv.py --check \
  --expected-runtime-manifest-hash 643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D \
  [repeatable approved --changed-file paths]
Rows: 155; added=[]; removed=[]; changed=[]
P0 build rows=41; P0 not implemented=48
PASS

python docs\fable\remaining_build\build_coverage_csv.py --decision-inventory
count=29 max=D-029 next_free=D-030 duplicates=[]

$env:PYTHONPATH='D:\TrendForge\backend'; python -m pytest -q backend\tests
534 passed in 99.69s

cd frontend
cmd /c npm test
135/135 checks passed
```

Automated runtime containment:

```text
protected source files: 119
before: 643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D
after:  643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D
```

Verdict: **VERIFIED** for the residual Single Build Spine governance closure.
This supersedes the weaker same-day 8-test/manual-manifest proof only. It does
not prove live source readiness, FMR runtime implementation, production
screening accuracy, source activation, quantity, orders or application-wide
production readiness.
## 2026-07-29 - Single Build Spine Structural Validation

Scope: existing governance documents, coverage generator/CSV and focused
adversarial tests. No runtime backend/frontend implementation was in scope.

Structural assertions now observed:

1. File A, Final Merge and remaining-build README contain one complete
   `FMR-001..011` table with identical normalized R-owner and linked-requirement
   maps.
2. Coverage FMR owners equal File A. `FMR-010` expands to all nineteen
   `R0-R18` owners; `FTR-034`, `STO-017` and `UI-009` remain linked
   requirements for `FMR-011`, not R owners.
3. Every Discovery `M0-M23`, `T0-T4` and `PK-A..PK-D` detail tag has a valid
   File A owner; no `UNMAPPED_STOP` remains.
4. Discovery and Options contain no independent M/T/PK build-order instruction.
5. Decision IDs are unique; D-025 owns the inventory compiler and D-029 owns
   Single Build Spine governance.
6. README and executable changed-file allowlists are exactly equal. Explicit
   paths outside the allowlist, including runtime `main.py`, fail closed.
7. Safe and unsafe fixtures cover owner-map mismatch, duplicate decisions,
   competing build phrases, missing owners and changed-file boundaries.
8. Coverage regeneration retained every requirement ID and reports zero drift.

Observed commands:

```text
python -m py_compile docs\fable\remaining_build\build_coverage_csv.py
PASS

python -m pytest -q docs\fable\remaining_build\test_build_coverage_csv.py
........ [100%]
8 passed in 0.11s

python docs\fable\remaining_build\build_coverage_csv.py --check [repeatable --changed-file paths]
Rows: 155; added=[]; removed=[]; changed=[]
P0 build rows=41; P0 not implemented=48
PASS

$env:PYTHONPATH='D:\TrendForge\backend'
python -m pytest -q backend\tests
534 passed in 126.57s

cd frontend
cmd /c npm test
135/135 checks passed
```

The first root-level backend attempt omitted the documented `PYTHONPATH` and
failed during collection with `ModuleNotFoundError: trendforge_api`. The corrected
documented invocation above passed; the collection failure was an invalid command,
not a runtime regression.

Runtime containment observation:

```text
backend/trendforge_api + frontend files: 240
before SHA-256 manifest: A560FF0834CBD6E89EB624B968485D37EC2D53565EA09EF4EA753F1CCE4367E8
after  SHA-256 manifest: A560FF0834CBD6E89EB624B968485D37EC2D53565EA09EF4EA753F1CCE4367E8
```

Verdict: **VERIFIED** for enforceable single-spine governance. This is not a
claim that market-data sources, screening features or the full application are
production-ready.

## 2026-07-29 - Dual-Spine Governance Cleanup Verification

Scope: documentation + coverage-generator governance checks only.

Observed:

```text
python docs\fable\remaining_build\build_coverage_csv.py --check
Rows: 155; added=[]; removed=[]; changed=[]
P0 build rows=41; P0 not implemented=48
PASS (exit 0)
```

Cross-file checks enforced by `validate_governance_docs`:

- FMR-001..011 present in CSV, File A, FINAL_MERGE, remaining_build README
- Discovery no longer claims sole coding spine
- Options requires FMR and scenario-only GEX wording
- fileindex has zero `___KEEP` placeholders
- Product HTML mentions FINAL_MERGE_PLAN + File A attribution
- DECISIONS contains D-025 and D-028
- FINAL_MERGE does not name Discovery as File B

Verdict: **VERIFIED** at governance-document ceiling. Detail tags map to File A R*; Final Merge remains mandatory addendum via Ã‚Â§25.21. No FMR product runtime or production readiness claimed. HTML remains static fixture preview only.

## 2026-07-28 - Final Merge Governance Validation

Scope: documentation and traceability only; no backend/frontend runtime behavior changed.

Observed checks:

```text
python -m py_compile docs\fable\remaining_build\build_coverage_csv.py
PASS

python docs\fable\remaining_build\build_coverage_csv.py --check
Rows: 154; added=[]; removed=[]; changed=[]
P0 build rows=40; P0 not implemented=47
```

A cross-file assertion verified all required pointers: `AGENTS.md`, File A section 25.21, remaining-build README section 10, remaining-project file map, decision D-028, fileindex section 6.2A, and coverage aliases `FMR-001` through `FMR-010`. CSV counts were exactly 154 total and 10 FMR rows.

Verdict: **VERIFIED** at the governance-document ceiling. `FINAL_MERGE_PLAN.md` is now mandatory for mapped product/design work but remains subordinate to File A build order, public states, permissions and acceptance. No FMR runtime feature or production readiness is claimed.

## Interactive system data-flow map audit (merged 2026-07-25)

> **Source:** former docs/AUDIT_interactive_system_data_flow_map_2026-07-25.md (merged here and removed)  
> **Map under test:** docs/interactive_system_data_flow_map.html  
> **Companion node guide:** docs/ARCHITECTURE.md section *System map node guide*  
> **This section is canonical.**


# AUDIT REPORT: TrendForge Interactive System Data-Flow Map (2026-07-23)

**Auditor role:** Senior systems architect + governance auditor  
**Artifact:** `docs/interactive_system_data_flow_map.html`  
**Code base date of evidence:** 2026-07-25 (live `D:\TrendForge`)  
**Authority:** `AGENTS.md` Ã¢â€ â€™ File A Ã¢â€ â€™ `BUILD_STATUS`/`VALIDATION` Ã¢â€ â€™ code/tests Ã¢â€ â€™ Hybrid File B  

---

## 1. EXECUTIVE SUMMARY

| Metric | Value |
|--------|------:|
| Overall Correctness Score | **72/100** |
| Critical Issues | **6** |
| Warnings (partial correctness) | **28** |
| Missing Components (checklist items) | **60+** |
| Governance Gaps | **5** |
| R0 Blockers reflected accurately | **Mostly yes** (activation=false is correct) |

### Critical issues (must fix in any Ã¢â‚¬Å“completeÃ¢â‚¬Â map)

1. **State vocabulary conflation (CRITICAL for CONFIRMED governance)**  
   Map uses WATCH / WAIT / CONFIRMED / REJECT as if they were the scannerÃ¢â‚¬â„¢s `statusGroup` and `final_state`. Code is different:
   - `models.StatusGroup` = only `ready` | `wait` | `reject`
   - `causal_engine.FinalState` includes `READY`, `WAIT`, `WAIT_DATA_WEAK`, `REJECT`, `NO_TRADE`, locksÃ¢â‚¬Â¦ Ã¢â‚¬â€ **not** product string `CONFIRMED`
   - Stage-2 label `CONFIRMED` is **execution-score label**, not radar public CONFIRMED
   - Q5 public four-state (`WATCH`/`WAIT`/`CONFIRMED`/`REJECT`) lives in `frontend/q5-contract.js` + selection fixtures, **not** in `scanner_scheduler` payload mapping
   - Live scanner maps almost everything non-reject to **`statusGroup: "wait"`** and never emits `"ready"`/`"confirmed"` from `_run_once`

2. **Scanner status_group mapping never promotes READY**  
   In `scanner_scheduler.py` ~546Ã¢â‚¬â€œ552: only `"reject"` or `"wait"`. Even if causal `final_state=="READY"`, radar group stays `wait`. Map step 13 is therefore **wrong** on Ã¢â‚¬Å“map to watch/wait/rejectÃ¢â‚¬Â.

3. **Primary path omits activation ceiling as a hard sequential gate**  
   Teal path jumps `candles Ã¢â€ â€™ scanner Ã¢â€ â€™ corpÃ¢â‚¬Â¦` without showing that **before symbol work**, global `gate_readiness()` + `sourceActivationReady=false` forces `source_gates_blocked=True` and injects `OFFICIAL_SOURCE_CONFIRMATION` WAIT on every causal candidate. That is the live product ceiling.

4. **Safety state machine mis-describable as GREENÃ¢â€ â€™YELLOWÃ¢â€ â€™ORANGEÃ¢â€ â€™RED**  
   Actual: `GREEN | RISK_REDUCED | COOLDOWN_ACTIVE | WAIT_EMOTIONAL_RISK | LOCKED_NO_TRADE | STOP_TRADING_NOW | BROKER_DATA_TRAUMA`. Map node is OK at high level; any YELLOW/ORANGE language is wrong.

5. **Edge `gates Ã¢â€ â€™ ui` is wrong topology**  
   UI source-health comes from `engine.list_source_health` Ã¢â€ â€™ `GET /api/source-health`, not from gate_readiness. Compiler maturity joins there; gates are separate (`GET /api/gates/readiness`).

6. **Edge `ui Ã¢â€ â€™ safety` bypasses API**  
   Panic lock is `POST /api/safety/panic-lock` via `api`, not a direct UIÃ¢â€ â€™safety edge. Correct: `ui Ã¢â€ â€™ api Ã¢â€ â€™ safety`.

### What the map gets right (high value)

- Boss path is **`ScannerScheduler._run_once`**, not dual engines  
- Location: `backend/trendforge_api/scanner_scheduler.py`  
- Research-only / no broker execution / `executable=False`  
- `sourceActivationReady=false`, gate-authorized 0  
- Critical source check Ã¢â€ â€™ parse Ã¢â€ â€™ gates Ã¢â€ â€™ safety Ã¢â€ â€™ context Ã¢â€ â€™ candles Ã¢â€ â€™ corp Ã¢â€ â€™ harmonic Ã¢â€ â€™ features/evidence Ã¢â€ â€™ causal Ã¢â€ â€™ persist Ã¢â€ â€™ radar  
- Side systems correctly demoted  
- R0 residual critical path vs ShadowFlow/CIE deferral  

---

## 2. VERIFICATION BY PROCESS STEP

| Step | Title | Verdict | Issue/Note |
|------|-------|---------|------------|
| 0 | Start Ã¢â‚¬â€ trigger | Ã¢Å“â€¦ | UI `POST /api/scanner/run-once`, scheduler thread, or API. Class `ScannerScheduler` + singleton `SCANNER_SCHEDULER`. Default interval 900s. |
| 1 | Exchange calendar | Ã¢Å“â€¦ | Scheduled only: `if trigger=="scheduler" and not calendar["canRunScheduledScan"]`. Manual can still run. Module `exchange_calendar.py`. |
| 2 | Source monitor critical keys | Ã¢Å¡Â Ã¯Â¸Â | Function correct. **Exact** `CRITICAL_SOURCE_KEYS` = `nse_bhavcopy_eod`, `nse_index_close_eod`, `nse_fno_ban`, `nse_large_deals`, `nse_participant_oi`, `nse_fii_dii`, `amfi_monthly_portfolio`, `cftc_cot`, `mcx_bhavcopy`. Map prose omits **index close** and **participant OI**. Does **not** include ASM/GSM (those are gate deps, not critical monitor set). |
| 3 | Parse sources | Ã¢Å“â€¦ | `parse_sources(CRITICAL_SOURCE_KEYS)`; fail-closed parser states; HTTP 200 Ã¢â€°Â  structured success. Then `emit_source_health_alerts`. |
| 4 | Gate readiness + compiler | Ã¢Å“â€¦ | `gate_readiness()`; if `not source_activation_ready` every gate forced `WAIT_SOURCE_ACTIVATION`. Mechanism: `compile_default_inventory()` Ã¢â€ â€™ `report.source_activation_ready` + per-contract `gate_permission` (workbook mtime/size cache). **Not** env var. |
| 5 | Trader safety | Ã¢Å¡Â Ã¯Â¸Â | Correct call. States are **not** Y/O/R ladder (see Ã‚Â§5.5). `executable: Literal[False]` on `SafetyStatus`. Panic creates `LOCKED_NO_TRADE` event. |
| 6 | Market / sector context | Ã¢Å“â€¦ | `build_official_market_context` / `build_official_sector_contexts`; `ContextDataUnavailable` collected; `_runtime_context_gate` Ã¢â€ â€™ PASS/WAIT/HARD_FAIL/STALE. |
| 7 | Create run + persist gates | Ã¢Å¡Â Ã¯Â¸Â | Order in code: monitor/parse/gates/safety/**context rebuild first**, then `create_scanner_run`, then gate decisions. Map implies create-run then context; **context is before create**. `run_hash` = SHA-256(`universe:trigger:iso_now`)[:16], integer `run_id` PK. On `critical_broken` Ã¢â€ â€™ `PAUSED` before symbols. |
| 8 | Universe Ã¢â€ â€™ candles | Ã¢Å¡Â Ã¯Â¸Â | `list_ohlcv_series(min_candles=40)`. Limits: WATCHLIST 5, NIFTY50 50, NIFTY200 25, NIFTY500 50. Non-watchlist forces TF in `{1d,1w}`. Candles from **SQLite OHLCV tables** primarily; Parquet is parallel store (`data/parquet/{tf}/{source}/{SYMBOL}.parquet`), not necessarily scan source. |
| 9 | Integrity Ã¢â€ â€™ harmonic Ã¢â€ â€™ lifecycle | Ã¢Å“â€¦ | `reconcile_corporate_actions` + `assess_adjustment_integrity`; PASS Ã¢â€ â€™ `analyze_harmonic_advanced`; else synthetic FAIL analysis `REJECT_DATA_INTEGRITY`; then `track_detected_harmonic`. |
| 10 | Features + evidence | Ã¢Å¡Â Ã¯Â¸Â | Calls correct. Features pin **manifest** (`FEATURE_VERSION` + registry/engine ids) Ã¢â‚¬â€ **not** full evaluation of all 39 FTR contracts on this path. Ã¢â‚¬Å“39 FTRÃ¢â‚¬Â is registry governance (DAT-010), stronger on Q5/selection binding than on every scanner feature dict field. |
| 11 | Causal candidate + symbol gates | Ã¢Å¡Â Ã¯Â¸Â | Adds STOCK_SURVEILLANCE, MARKET, SECTOR, TRADER_SAFETY **and** earlier `CAUSE_SPONSOR_REQUIRED`, `OFFICIAL_SOURCE_CONFIRMATION`, `POINT_IN_TIME_FEATURES`, optional `SOURCE_TIMEZONE`. Map under-lists. |
| 12 | Causal batch | Ã¢Å“â€¦ | `evaluate_causal_batch`; layers CAUSEÃ¢â€°Â¤6 SPONSORÃ¢â€°Â¤10 STRUCTUREÃ¢â€°Â¤6 FLOWÃ¢â€°Â¤6; minima 2/4/2/2; defaults min total 18, min layers 3, min percentile; independence 0.3Ãƒâ€”min shared raw keys across layers. |
| 13 | Merge precedence Ã¢â€ â€™ save | Ã¢ÂÅ’ | Precedence list mostly right (safety lock > integrity > market HARD_FAIL > sector HARD_FAIL > surveillance > emotional waitÃ¢â‚¬Â¦). **Wrong:** Ã¢â‚¬Å“map to watch/wait/rejectÃ¢â‚¬Â and product **CONFIRMED**. Code: `statusGroup` Ã¢Ë†Ë† {`wait`,`reject`} only; `type` hardcoded `"harmonic"`; `executable: False` always; false-screen reason explicitly says stored scanner never emits executable READY. Stage2 `CONFIRMED` is score label only. |
| 14 | Radar Ã¢â€ â€™ UI | Ã¢Å¡Â Ã¯Â¸Â | `engine._latest_real_candidates`: `list_scanner_runs(limit=1)` **ORDER BY started_at DESC** Ã¢â‚¬â€ not Ã¢â‚¬Å“COMPLETE onlyÃ¢â‚¬Â. Empty + `TRENDFORGE_DEMO_MODE` Ã¢â€ â€™ mock. UI loads via **HTTP Promise.all** once (no WS/SSE poll loop for radar). |
| 15 | Side systems | Ã¢Å“â€¦ | Q5, deriv, institutional, risk (qty always 0), OpenAlgo capability/read-only, TradeVision evidence export Ã¢â‚¬â€ not scan boss. |

---

## 3. VERIFICATION BY NETWORK NODE

| Node ID | Label | Kind | Verdict | Issue/Note |
|---------|-------|------|---------|------------|
| ui | Frontend Panel | ui | Ã¢Å“â€¦ | `frontend/index.html` + `app.js` + `q5-contract.js`. |
| api | FastAPI main | hub | Ã¢Å“â€¦ | `main.py`, `run_server.py` 127.0.0.1:8000; CORS + request audit middleware only (no auth DI). |
| scanner | Scanner Scheduler | engine | Ã¢Å“â€¦ | Path correct. Threading daemon, not asyncio task queue. |
| monitor | Source Monitor | engine | Ã¢Å“â€¦ | `source_monitor.py`; institutional_sources for NSE session. |
| parser | Source Parser | engine | Ã¢Å“â€¦ | `source_parser.py` + `parsers/*`. |
| compiler | Inventory Compiler | gov | Ã¢Å“â€¦ | `source_inventory_compiler.py` + key map + overlaps. |
| gates | Gate Readiness | engine | Ã¢Å“â€¦ | G03/G01/G12/G13/MCX. |
| safety | Safety Engine | engine | Ã¢Å¡Â Ã¯Â¸Â | States list incomplete on map. |
| calendar | Exchange Calendar | engine | Ã¢Å“â€¦ | |
| context | Market Context | engine | Ã¢Å“â€¦ | Also sector RRG snapshots. |
| candles | OHLCV / Parquet | store | Ã¢Å¡Â Ã¯Â¸Â | Dual store: SQLite candles **and** Parquet; scan uses `list_ohlcv_*` (SQLite). Label overweights Parquet. |
| corp | Corporate Actions | engine | Ã¢Å“â€¦ | |
| harmonic | Harmonic Engine | engine | Ã¢Å¡Â Ã¯Â¸Â | Should split detector vs advanced (see Ã‚Â§5.6). Patterns: Gartley, Bat, Butterfly, Crab, Deep Crab, Cypher, Shark, 5-0, ABCD, AB=CD. |
| lifecycle | Harmonic Lifecycle | engine | Ã¢Å“â€¦ | `harmonic_lifecycle.py` + `harmonic_scan_lifecycle.py`; pattern_key identity. |
| features | Feature Engineering | engine | Ã¢Å¡Â Ã¯Â¸Â | Registry pin partial. |
| evidence | Evidence Builder | engine | Ã¢Å“â€¦ | |
| causal | Causal Engine | engine | Ã¢Å¡Â Ã¯Â¸Â | Final states / Stage1Ã¢â‚¬â€œ2 labels not shown. |
| storage | SQLite Storage | store | Ã¢Å“â€¦ | `data/trendforge.db` (+ research db path variants). |
| engine_radar | Radar Engine | engine | Ã¢Å“â€¦ | `engine.list_candidates`. |
| risk | Risk Engine | side | Ã¢Å“â€¦ | `quantity=0`, `executable=False`, state `POSTPONED_NO_QUANTITY`. |
| q5 | Q5 Selection | side | Ã¢Å¡Â Ã¯Â¸Â | Four-state public contract is Q5; must not merge with scanner StatusGroup. |
| deriv | Derivatives Engine | side | Ã¢Å“â€¦ | BS/IV only. |
| inst | Institutional Stack | side | Ã¢Å“â€¦ | |
| ext | External Markets | external | Ã¢Å“â€¦ | Registry + raw_sources. |
| openalgo | OpenAlgo | external | Ã¢Å“â€¦ | Read-only routes; forbidden placeorder/etc terms. |

**Missing nodes (not on map):** `source_scheduler` (monitor jobs), `operational_alerts`, `records` (alerts/journal), `nse_session` / resample, `market_activity`, `disclosure_intelligence`, `validation_engine`, `scanners/pk_compatibility` (shadow), `feature_registry` as governance node, `raw_source_archive` store, dual DB `trendforge_research.db`.

---

## 4. VERIFICATION BY NETWORK EDGE

| From | To | Strength | Verdict | Issue/Note |
|------|----|----------|---------|------------|
| ext Ã¢â€ â€™ monitor | path | Ã¢Å“â€¦ | Fetch/archive primary. |
| monitor Ã¢â€ â€™ parser | path | Ã¢Å“â€¦ | |
| parser Ã¢â€ â€™ storage | path | Ã¢Å“â€¦ | Parse results / domain rows in SQLite. |
| candles Ã¢â€ â€™ scanner | path | Ã¢Å¡Â Ã¯Â¸Â | Scanner also **pulls** candles (scannerÃ¢â€ â€™candles strong exists). Path should show storage/SQLite candles origin more clearly. |
| scanner Ã¢â€ â€™ corp | path | Ã¢Å“â€¦ | |
| corp Ã¢â€ â€™ harmonic | path | Ã¢Å¡Â Ã¯Â¸Â | Only if integrity PASS; else bypass with FAIL analysis (still continues). |
| harmonic Ã¢â€ â€™ features | path | Ã¢Å¡Â Ã¯Â¸Â | Features built from candles independently; order is harmonic then features, not strict harmonic output as feature input. |
| evidence Ã¢â€ â€™ causal | path | Ã¢Å“â€¦ | |
| features Ã¢â€ â€™ causal | path | Ã¢Å“â€¦ | |
| harmonic Ã¢â€ â€™ causal | path | Ã¢Å“â€¦ | Via `scanner_causal`. |
| causal Ã¢â€ â€™ storage | path | Ã¢Å“â€¦ | Candidates + many `save_gate_decision`s. |
| storage Ã¢â€ â€™ engine_radar | path | Ã¢Å“â€¦ | Latest run by `started_at DESC`. |
| engine_radar Ã¢â€ â€™ ui | path | Ã¢Å“â€¦ | |
| ui Ã¢â€ â€™ api | strong | Ã¢Å“â€¦ | |
| api Ã¢â€ â€™ scanner | strong | Ã¢Å“â€¦ | |
| api Ã¢â€ â€™ engine_radar | strong | Ã¢Å“â€¦ | |
| scanner Ã¢â€ â€™ monitor/parser/gates/safety/calendar/context/candles/lifecycle/evidence/causal/storage | strong | Ã¢Å“â€¦ | Direct function calls, no bus. |
| compiler Ã¢â€ â€™ gates | strong | Ã¢Å“â€¦ | Activation ceiling. |
| compiler Ã¢â€ â€™ engine_radar | strong | Ã¢Å“â€¦ | Maturity on source-health. |
| gates Ã¢â€ â€™ scanner | strong | Ã¢Å“â€¦ | blocked flag. |
| safety Ã¢â€ â€™ scanner | strong | Ã¢Å“â€¦ | |
| context Ã¢â€ â€™ scanner | strong | Ã¢Å“â€¦ | |
| candles Ã¢â€ â€™ corp/harmonic/features | strong | Ã¢Å“â€¦ | |
| harmonic Ã¢â€ â€™ lifecycle | strong | Ã¢Å“â€¦ | |
| api Ã¢â€ â€™ storage | strong | Ã¢Å“â€¦ | |
| monitor Ã¢â€ â€™ storage | strong | Ã¢Å“â€¦ | |
| ext Ã¢â€ â€™ candles | strong | Ã¢Å“â€¦ | Adapters/EOD. |
| api Ã¢â€ â€™ risk/q5/deriv/inst/compiler/openalgo | weak | Ã¢Å“â€¦ | |
| openalgo Ã¢â€ â€™ candles | weak | Ã¢Å“â€¦ | Optional history adapter. |
| **ui Ã¢â€ â€™ safety** | weak | Ã¢ÂÅ’ | Must be uiÃ¢â€ â€™apiÃ¢â€ â€™safety. |
| features Ã¢â€ â€™ q5 | weak | Ã¢Å¡Â Ã¯Â¸Â | Loose; Q5 binds registry via selection contracts, not scanner features edge. |
| storage Ã¢â€ â€™ ui | weak | Ã¢Å¡Â Ã¯Â¸Â | Via API only. |
| **gates Ã¢â€ â€™ ui** | weak | Ã¢ÂÅ’ | Wrong; source-health/gates are separate API paths. |

**Missing edges (examples):**  
scanner Ã¢â€ â€™ operational_alerts; safety Ã¢â€ â€™ storage (events); api Ã¢â€ â€™ trade_vision; parser Ã¢â€ â€™ evidence (indirect via domain rows); calendar Ã¢â€ â€™ scanner (already); compiler Ã¢â€ â€™ source_contracts/coverage APIs; frontend Ã¢â€ â€™ q5-contract for selection normalize; risk never Ã¢â€ â€™ scanner (correct absence).

---

## 5. MISSING CONNECTIONS & DETAILS

### 5.1 Data & State Layer
- [ ] Raw sources: `data/raw_sources/{source_key}/Ã¢â‚¬Â¦` binaries + `raw_source_archive` SQLite (content_hash, raw_path)
- [ ] Structured: SQLite tables `source_snapshots`, parse results, domain rows, `evidence_claims`, `gate_decisions`, `scanner_runs`, `scanner_candidates`
- [ ] Parquet layout: `data/parquet/{timeframe}/{source}/{SYMBOL}.parquet` (not by date partition)
- [ ] `scanner_runs`: id PK, `run_hash` sha256[:16], universe, trigger, status, paused_reason, candidate_count, started_at, finished_at, gate_readiness_json, source_health_json
- [ ] `scanner_candidates`: run_id, symbol, final_state, status_group, quality_score, gate_ratio, payload_json, false_screen_reason
- [ ] `RadarCandidate` model fields (symbol, type, state, statusGroup ready|wait|reject, metrics, proof, risk, seriesÃ¢â‚¬Â¦) Ã¢â‚¬â€ **narrower** than full payload_json
- [ ] No Redis/cache between FE and BE
- [ ] Demo: only if latest run empty/absent **and** `TRENDFORGE_DEMO_MODE` in {1,true,yes,on}

### 5.2 Frontend Architecture
- [ ] Bootstrap: `loadApiData()` Promise.all command-bar, radar, safety, market latest, calendar, source-health
- [ ] Transport: **HTTP fetch only** (no WebSocket/SSE); manual refresh for source-health; recovery dialog 1s timer only
- [ ] `q5-contract.js`: maps READY*Ã¢â€ â€™WATCH; PUBLIC_STATES WATCH/WAIT/CONFIRMED/REJECT; validates Q5-R6 fixtures
- [ ] Panic: click Ã¢â€ â€™ immediate POST panic-lock (no confirm dialog); if locked Ã¢â€ â€™ recovery modal
- [ ] Filters UI include watch/confirmed but backend StatusGroup lacks watch; Q5 normalizer bridges some cases
- [ ] file:// uses `API_BASE=http://127.0.0.1:8000`

### 5.3 Backend Architecture
- [ ] No FastAPI Depends auth/DB session DI; modules call `storage.connect()` per op
- [ ] Scanner: **threading.Thread** daemon + `threading.Lock`; sequential symbol loop then one causal batch
- [ ] Source monitor fail mid-run: exceptions Ã¢â€ â€™ run status ERROR; critical broken gates Ã¢â€ â€™ PAUSED zero candidates; partial parse allowed (blocked flag)
- [ ] Direct function calls only (no event bus/MQ)
- [ ] Pydantic models on many routes; no global rate limit middleware
- [ ] Path: `backend/trendforge_api/scanner_scheduler.py`
- [ ] Latest run: `ORDER BY started_at DESC, id DESC LIMIT 1` (not COMPLETE filter)

### 5.4 Governance & Compiler
- [ ] Gates: G03 ASM/GSM; G01 FII/DII+participant OI+NSDL FPI; G12 AMFI+large deals+PIT/SAST+buyback/offer+pledge; G13 participant OI+F&O ban+MWPL%+SLB+FO bhav+OI spurts; MCX mcx_bhav+cftc+WGC+SGE+usd_inr
- [ ] PASS_REQUIREMENTS subsets differ from full dependency key lists (e.g. G01 only needs nse_fii_dii to PASS)
- [ ] `sourceActivationReady`: **compiler report boolean**, default false; gates demote PASSÃ¢â€ â€™WAIT_SOURCE_ACTIVATION
- [ ] H1A0 **6/6** = acceptance checks H1A0-01Ã¢â‚¬Â¦06 (normalized inventory quality), **not** Ã¢â‚¬Å“6 defect classesÃ¢â‚¬Â
- [ ] Defect classes = **11** Hybrid Ã‚Â§16.4 codes in `HYBRID_H1A0_DEFECT_CODES`
- [ ] Coverage CSV 144 rows = plan requirement IDs (Q5/R/CROSS/TDG/HYBRIDÃ¢â‚¬Â¦), statuses PLANNED/PARTIAL/IMPLEMENTEDÃ¢â‚¬Â¦ Ã¢â‚¬â€ **not** one row = one test
- [ ] File A: research-only, four-state product model, no quantity/execution; File B formulas when Ã‚Â§0.5/Ã‚Â§25/README Ã‚Â§9 points

### 5.5 Safety & Audit
- [ ] State machine as coded (not traffic-light colors)
- [ ] Recovery: 5 checklist booleans all true on unlock
- [ ] executable=False: Pydantic `Literal[False]` + risk hardcode qty 0 (not auth middleware)
- [ ] Panic: no multi-user auth Ã¢â‚¬â€ localhost single-user anyone who can hit API
- [ ] Audit rows in SQLite gate_decisions, safety_events, general_alerts, request logs via middleware

### 5.6 Harmonic & Causal Systems
- [ ] detector: pivots + optional pyharmonics (license-gated env); advanced: ratio table multi-pattern + gates
- [ ] Lifecycle pattern_key / conflict statuses WAIT_TIMEZONE, WAIT_LEVELS, CONFLICT_DATA_REVISIONÃ¢â‚¬Â¦
- [ ] Stage1 max 28; Stage2 max 16 threshold 12 for stage2 CONFIRMED label
- [ ] Production READY blocked by unofficial evidence, waits, activation, missing cause/sponsor
- [ ] Product CONFIRMED (Q5) Ã¢â€°Â  causal READY Ã¢â€°Â  stage2 CONFIRMED

### 5.7 Source & Data Integrity
- [ ] Exact CRITICAL list (9 keys)
- [ ] Parser output: structured JSON payloads + parser_state enum, not free-form Parquet
- [ ] Overlaps: typed registry 20 parent/child, 6 alias, 3 distinct-shared (CROSS-001)
- [ ] Raw vs adjusted: corporate_actions integrity + CROSS-020 residual

### 5.8 Q5 Selection & Fixtures
- [ ] Four-state DTOs for selection radar/inspector
- [ ] Q5-R0Ã¢â‚¬Â¦R7 implemented at fixture ceilings
- [ ] Parallel path to scanner; not interchangeable

### 5.9 Integration Boundaries
- [ ] OpenAlgo: history/optionchain/greeks read-only; forbids placeorder/account/etc; capability report
- [ ] TradeVision: HMAC-signed JSON evidence export schema `trendforge-tradevision-evidence.v1` from latest COMPLETE run Ã¢â‚¬â€ not OMS
- [ ] No broker write path in repo (forbidden OpenAlgo terms; AGENTS ban)
- [ ] Unofficial cannot unlock production READY (causal + AGENTS)

### 5.10 Deferred / Rejected
- [ ] ShadowFlow/CIE: idea docs in `grok_plan/`, not tested thresholds Ã¢â‚¬â€ deferred not coded
- [ ] React/Redis: deferred; vanilla FE sufficient for single-user
- [ ] OMS: REJECTED boundary
- [ ] Quantity UI: POSTPONED File A

### 5.11 DevOps / Infrastructure
- [ ] Local: `python backend/run_server.py` / uvicorn; Docker multi-stage slim + HEALTHCHECK `/api/health`
- [ ] DB migrations in `storage.py` schema_migrations
- [ ] Coverage CSV via `docs/fable/remaining_build/build_coverage_csv.py` seed rows
- [ ] Health: `/api/health` guarded-research mode; no Prometheus `/metrics` found in map scope

---

## 6. CORRECTED END-TO-END FLOW

### One true research scan path (code-accurate)

1. **UI or API trigger**  
   `frontend/app.js` Ã¢â€ â€™ `POST /api/scanner/run-once?universe=WATCHLIST_ONLY&fetch=false`  
   or `ScannerScheduler.start` daemon every N seconds with `trigger="scheduler"`.

2. **Calendar gate (scheduler only)**  
   `evaluate_nse_calendar()`; if scheduled and not `canRunScheduledScan` Ã¢â€ â€™ return calendar state, no run.

3. **Acquire + structure critical sources**  
   `check_sources(CRITICAL_SOURCE_KEYS[9])` Ã¢â€ â€™ raw archive/snapshots  
   `parse_sources(...)` Ã¢â€ â€™ structured parse rows or fail-closed states  
   `emit_source_health_alerts`.

4. **Compiler-capped gate readiness**  
   `gate_readiness()` joins `compile_default_inventory()`:  
   - global `sourceActivationReady` (currently **false**)  
   - per-contract `gatePermission` (currently **none authorize**)  
   Fresh structured data demoted to `WAIT_SOURCE_ACTIVATION` / `WAIT_SOURCE_GATE_PERMISSION`.  
   Aggregate: if any `tradeGateEffect != CAN_CONFIRM` Ã¢â€ â€™ `blocked=True` for all symbols.

5. **Trader safety**  
   `evaluate_safety_status()` from journal + safety_events + risk settings.  
   Locking states force later HARD_FAIL / final lock states. Always non-executable.

6. **Official context rebuild**  
   Market + sector snapshots; runtime gate outcomes; alerts on wait/regime change.

7. **Open lineage run**  
   `create_scanner_run` with `run_hash=sha256(universe:trigger:now)[:16]`.  
   Persist EXCHANGE_CALENDAR, each dependency gate, TRADER_SAFETY, MARKET_CONTEXT.  
   If any gate `BLOCKED_SOURCE_BROKEN` Ã¢â€ â€™ `finish PAUSED`, **stop** (no symbols).

8. **Universe of stored series**  
   SQLite OHLCV series with Ã¢â€°Â¥40 candles; universe limit + TF filters.

9. **Per symbol (sequential)**  
   - Load candles  
   - Corporate action reconcile + adjustment integrity  
   - Harmonic advanced (or integrity FAIL analysis)  
   - Lifecycle track  
   - PIT features (manifest pin; engine mismatch Ã¢â€ â€™ non-OK state)  
   - External evidence claims persist  
   - Build causal candidate + multi gates (cause/sponsor floors, official blocked, surveillance, market/sector/safety, feature integrity)

10. **Batch causal**  
    Independence penalties on shared `rawInputKeys`; Stage1 Ã¢â€°Â¤28 eligibility; Stage2 optional execution score (scanner path usually no live execution object Ã¢â€ â€™ Stage2 NOT_RUN/BLOCKED); `executable=False`.

11. **Precedence merge**  
    Locks / integrity / market HARD_FAIL / sector HARD_FAIL / surveillance / emotional / lifecycle WAIT / weak data override causal.  
    **statusGroup** = `reject` | `wait` only. Payload `type="harmonic"`, `executable: false`.

12. **Persist**  
    Per-symbol gate_decisions + `save_scanner_candidate` + `finish_scanner_run(COMPLETE)`.

13. **Radar materialize**  
    `list_scanner_runs(limit=1)` by started_at; validate payloads as `RadarCandidate`; filter mode/status/tf/search.  
    Demo mock only if empty and env demo on.

14. **UI paint**  
    Command bar forces `system=RESEARCH_ONLY`; safety/calendar/vix/regime pills; radar list filters by statusGroup; inspector shows reasons/metrics.  
    Q5 contract may remap READYÃ¢â€ â€™WATCH for selection fixtures Ã¢â‚¬â€ **separate lane**.

### R0 Ã¢â€ â€™ R1 Ã¢â€ â€™ R2 maturity (governance, not scan steps)

| Stage | Meaning | Scan impact |
|-------|---------|-------------|
| **R0 residual** | Living map/compiler done; activation false; maturity history, mirror/resolver, extended fields, raw/adjusted open | Gates stay WAIT_ACTIVATION; no product CONFIRMED |
| **R1** | Selection DTO / radar contract hardening | UI four-state honesty; still research |
| **R2** | Live S0Ã¢â‚¬â€œS3 cheap pipeline + PRF sources | Broader live structure/flow; still no broker |

Until activation milestones flip compiler permissions **and** File A allows, CONFIRMED remains non-authorizable.

---

## 7. RECOMMENDED UPDATES TO `interactive_system_data_flow_map.html`

1. **Reword Step 13** Ã¢â‚¬â€ Replace CONFIRMED/watch mapping with: `statusGroup Ã¢Ë†Ë† {wait, reject}`; causal may compute READY but scanner forces research wait; Q5 four-state is side path.  
2. **Split Step 7** Ã¢â‚¬â€ Context rebuild **before** create_scanner_run; show PAUSED branch.  
3. **Expand Step 2** Ã¢â‚¬â€ Print all 9 CRITICAL keys.  
4. **Expand Step 11** Ã¢â‚¬â€ List all gate codes injected by `scanner_causal` + scheduler.  
5. **Add Step callout** Ã¢â‚¬â€ Ã¢â‚¬Å“Activation ceiling: blocked flag on every candidateÃ¢â‚¬Â.  
6. **Fix nodes** Ã¢â‚¬â€ Split `harmonic`Ã¢â€ â€™`harmonic_detector` + `harmonic_advanced`; split candles into `ohlcv_sqlite` + `parquet_optional`; add `raw_archive`, `ops_alerts`, `records`.  
7. **Fix edges** Ã¢â‚¬â€ Remove `uiÃ¢â€ â€™safety`, `gatesÃ¢â€ â€™ui`; add `uiÃ¢â€ â€™apiÃ¢â€ â€™safety`, `apiÃ¢â€ â€™source-healthÃ¢â€ â€™ui`, `apiÃ¢â€ â€™gates-readinessÃ¢â€ â€™ui`, `scannerÃ¢â€ â€™ops_alerts`.  
8. **Primary path** Ã¢â‚¬â€ Include `compilerÃ¢â€ â€™gatesÃ¢â€ â€™scanner(blocked)` as teal governance segment.  
9. **Side panel copy** Ã¢â‚¬â€ Document FinalState vs Stage2 CONFIRMED vs Q5 CONFIRMED.  
10. **Milestone card** Ã¢â‚¬â€ Add Ã¢â‚¬Å“State vocabulary triple-split (CRITICAL)Ã¢â‚¬Â governance gap.  
11. **Matrix** Ã¢â‚¬â€ Recompute after edge fixes.  
12. **Optional Tab 5** Ã¢â‚¬â€ Coverage CSV open P0 IDs deep-linked to modules from `PLAN_REQUIREMENT_COVERAGE.csv`.

---

## 8. GOVERNANCE COMPLIANCE CHECKLIST

- [x] File A constraints respected **in map intent** (research-only, no OMS)  
- [x] File B not treated as build authority  
- [x] H1A0 6/6 mentioned as done Ã¢â‚¬â€ **label needs precision** (6 acceptance checks, 11 defect classes)  
- [x] No executable quantity product path (risk engine correct)  
- [x] No broker secret leakage path claimed  
- [ ] **No CONFIRMED unlock without activation** Ã¢â‚¬â€ map wording risks equating stage2/Q5/product CONFIRMED (**fix vocabulary**)  
- [x] Coverage 144 rows snapshot matches last BUILD_STATUS audit  
- [ ] **UI filter Ã¢â‚¬Å“confirmed/watchÃ¢â‚¬Â vs backend StatusGroup** Ã¢â‚¬â€ honesty gap remains in product UI, should be flagged on map  
- [x] OpenAlgo forbidden order routes documented in code  
- [x] TradeVision is evidence export not execution  

### Items that could accidentally unlock CONFIRMED / live trading if misunderstood

| Item | Risk |
|------|------|
| Calling stage2 label `CONFIRMED` Ã¢â‚¬Å“product CONFIRMEDÃ¢â‚¬Â | CRITICAL documentation hazard |
| Assuming `statusGroup: ready` from scanner | Code currently wonÃ¢â‚¬â„¢t emit it from `_run_once` |
| Flipping `sourceActivationReady` without File A activation milestone | Would change gate_state PASS paths Ã¢â‚¬â€ **must be gated process** |
| Enabling OpenAlgo write routes | Explicitly forbidden; code lists placeorder terms |
| Treating risk `quantity` field as live size if someone reverts qty=0 hardcode | CRITICAL if regression |

---

## APPENDIX A Ã¢â‚¬â€ Exact gate dependency summary

| Code | Name | Keys (dependency list) | PASS subset |
|------|------|------------------------|-------------|
| G03_STOCK_SAFETY | ASM/GSM | nse_asm, nse_gsm | both |
| G01_INSTITUTIONAL_REGIME | FII/DII regime | nse_fii_dii, nse_participant_oi, nsdl_fpi_daily | nse_fii_dii |
| G12_SMART_MONEY | Smart money | amfi_monthly_portfolio, amfi_scheme_wise, nse_large_deals, sebi_pit_sast, bse_buyback_tender, bse_takeover_open_offer, nse_pledge_data | nse_large_deals |
| G13_OI_CONFIRMS | OI/MWPL/basis | nse_participant_oi, nse_fno_ban, nse_mwpl_percentages, nse_slb, nse_fo_bhavcopy, nse_oi_spurts | ban OR mwpl% OR fo bhav |
| MCX_CONTEXT | Commodity | mcx_bhavcopy, cftc_cot, world_gold_council_oi, wgc_gold_etf_holdings, wgc_gold_etf_flows, sge_daily_report, usd_inr | mcx_bhav+cftc+usd_inr |

---

## APPENDIX B Ã¢â‚¬â€ Causal layer numbers

| Layer | Max | Min pass |
|-------|----:|---------:|
| CAUSE | 6 | 2 |
| SPONSOR | 10 | 4 |
| STRUCTURE | 6 | 2 |
| FLOW | 6 | 2 |
| Stage1 total default | 28 | Ã¢â€°Â¥18 and Ã¢â€°Â¥3 layers and percentile gate |
| Stage2 | 16 | score Ã¢â€°Â¥12 Ã¢â€ â€™ stage2Label CONFIRMED |

Independence: shared `rawInputKeys` across layers Ã¢â€ â€™ penalty `0.3 * min(strengths)` split across the two layers.

---

## APPENDIX C Ã¢â‚¬â€ Evidence files used for this audit

- `backend/trendforge_api/scanner_scheduler.py`
- `backend/trendforge_api/gate_readiness.py`
- `backend/trendforge_api/engine.py`
- `backend/trendforge_api/causal_engine.py`
- `backend/trendforge_api/scanner_causal.py`
- `backend/trendforge_api/safety_engine.py`
- `backend/trendforge_api/risk_engine.py`
- `backend/trendforge_api/feature_engineering.py`
- `backend/trendforge_api/harmonic_advanced.py` / `harmonic_detector.py`
- `backend/trendforge_api/source_inventory_compiler.py`
- `backend/trendforge_api/storage.py` (schemas)
- `backend/trendforge_api/parquet_store.py`
- `backend/trendforge_api/openalgo_client.py`
- `backend/trendforge_api/trade_vision_export.py`
- `backend/trendforge_api/models.py`
- `frontend/app.js`, `frontend/q5-contract.js`
- `docs/interactive_system_data_flow_map.html`
- `Dockerfile`, `AGENTS.md`, `docs/BUILD_STATUS.md`

---

**End of audit.** Overall: the map is a **strong orientation tool (~72%)** for the real boss path and governance posture, but it is **not production-complete** until state vocabulary, activation-as-path, edge topology, and storage dual-paths are corrected.


---

# Validation

## 2026-07-23 - CROSS-002 Source-Key Governance Verification

The immutable workbook remained unchanged. The compiler now separates named
source keys from generated endpoint lineage and exposes an exact reviewed map.

| Contract | Observed result |
| --- | ---: |
| Named inventory source keys | 118 |
| Generated endpoint-lineage identities | 197 |
| Runtime catalog keys | 74 |
| Shared inventory/runtime keys | 63 |
| Inventory-only keys | 55 |
| Runtime-only keys | 11 |
| Unique living source keys | 129 |
| Normalized endpoints | 351 |
| Unassigned endpoint lineage | 192 |
| Reviewed / unreviewed source keys | 129 / 0 |
| Gate-authorized source keys | 0 |
| Source governance ready | true |
| Source activation ready | false |
| Execution authorized | 0 |

Commands and observed results:

```text
cd D:\TrendForge\backend
python -m pytest tests\test_source_inventory_compiler.py -q
28 passed

python -m pytest -q
533 passed in 110.73s

python -m ruff check trendforge_api\source_key_map_review.py trendforge_api\source_inventory_compiler.py tests\test_source_inventory_compiler.py
All checks passed

cd D:\TrendForge\frontend
npm test
135/135 checks passed

cd D:\TrendForge
python docs\fable\remaining_build\build_coverage_csv.py --check
Rows: 144; added=[]; removed=[]; changed=[]
```

Adversarial behavior: a fixture with a changed key set reports baseline drift,
zero reviewed keys, explicit unassigned endpoint lineage, no gate eligibility
and `sourceGovernanceReady=false`. A valid reviewed map still keeps
`sourceActivationReady=false`; review completion cannot self-authorize data.

## 2026-07-23 - CROSS-001 / H1A0-04 Verified

Observed the immutable master workbook through the compiler and read-only API.
The workbook SHA-256 before and after the milestone is
`1f76dab1c75252aa8185c97f69fc4e6f74b5710918b9d4b3e4a1566d9c646a43`.

| Check | Expected rule | Result | Observed evidence |
| --- | --- | --- | --- |
| H1A0-01 | No malformed source-key cells in normalized endpoints | PASS | `normalized_malformed=0; raw_key_prefix=29; raw_json_keys=16` |
| H1A0-02 | One URL per compiled endpoint | PASS | `normalized_compound=0; raw_compound=2` |
| H1A0-03 | Sentinel values excluded from canonical URLs | PASS | `normalized_sentinels=0; raw_sentinels=4` |
| H1A0-04 | Zero unexplained overlap, complete lineage, valid registry | PASS | `unexplained_overlap=0; invalid_resolution=0; stale_resolution=0; covered=370; rows=370` |
| H1A0-05 | Every canonical row has role and explicit use limits | PASS | `endpoints=351; contracts=315` |
| H1A0-06 | F&O ban and MWPL remain separate runtime contracts | PASS | `split=True; runtime_mismatch=0` |

The 29 exact reviewed overlap records comprise 20 `PARENT_CHILD_CONTRACT`, six
`SAME_DATASET_ALIAS` and three `DISTINCT_SHARED_ENDPOINT` records. There are no
active transport-variant or unproven-quarantine records.

Adversarial coverage proves unexplained overlap failure, typed exact matching,
stale contract-set rejection, wildcard rejection, weak-evidence alias
rejection, duplicate/conflicting registry failure, transport/distinct/quarantine
states, parent/child job preservation, URL-normalization collision handling,
per-URL compound binding, immutable hash enforcement, no source activation and
zero execution authority.

~~~text
python -m pytest tests\\test_source_inventory_compiler.py -q
26 passed in 5.00s

python -m pytest -q
531 passed in 100.62s

npm test
135/135 checks passed

python -m compileall -q trendforge_api tests\\test_source_inventory_compiler.py
passed

python -m ruff check trendforge_api\\source_inventory_compiler.py trendforge_api\\source_overlap_resolutions.py tests\\test_source_inventory_compiler.py
All checks passed

python -m ruff format --check trendforge_api\\source_inventory_compiler.py trendforge_api\\source_overlap_resolutions.py tests\\test_source_inventory_compiler.py
3 files already formatted

python docs\\fable\\remaining_build\\build_coverage_csv.py --check
Rows: 144; added=[]; removed=[]; changed=[]
~~~

Observed `GET /api/source-inventory/compiler-report`: HTTP 200, H1A0 6/6,
zero semantic-overlap defects, `resolutionRegistryValid=true`, lineage 370/370,
`sourceActivationReady=false`, unresolved contracts 315 and
`executionAuthorizedCount=0`. HTTP 200 is transport evidence only; the payload
assertions above establish this milestone's behavior.

## 2026-07-22 - H1A0 5/6 Versus 6/6 Reconciliation

This single-milestone verification resolves the contradictory H1A0 reports.

~~~text
cd D:\TrendForge\backend
python -m pytest tests\test_source_inventory_compiler.py -q
  19 passed in 7.40s
python -m pytest -q
  524 passed in 88.54s
python -m compileall -q trendforge_api tests
python -m ruff check tests\test_source_inventory_compiler.py trendforge_api\source_inventory_compiler.py
  All checks passed

cd D:\TrendForge\frontend
npm test
  135/135 checks passed

cd D:\TrendForge
python docs\fable\remaining_build\build_coverage_csv.py --check
  Rows: 144; added=[]; removed=[]; changed=[]
~~~

Observed `GET /api/source-inventory/compiler-report`:

| Check | Expected rule | Actual | Evidence / failure reason |
|---|---|---|---|
| H1A0-01 | Zero malformed source-key cells in normalized view | PASS | `normalized_malformed=0; raw_key_prefix=29; raw_json_keys=16` |
| H1A0-02 | One URL per normalized endpoint | PASS | `normalized_compound=0; raw_compound=2` |
| H1A0-03 | Sentinels stay outside canonical URL fields | PASS | `normalized_sentinels=0; raw_sentinels=4` |
| H1A0-04 | Zero unexplained contract overlap and complete lineage | FAIL | `unexplained_overlap=32; covered=370; rows=370`; lineage does not prove deduplication |
| H1A0-05 | Every canonical record has role, purpose, safe use, blocked use and next action | PASS | `endpoints=351; contracts=317` |
| H1A0-06 | F&O ban and MWPL percentages remain separate runtime contracts | PASS | `split=True; runtime_mismatch=0` |

The result is **5/6**. Raw workbook defects remain audit evidence; normalized
transport checks 1-3 pass; semantic acceptance check 4 fails; source activation
remains false; gate authorization and execution authorization remain zero. A
new adversarial fixture proves that complete lineage cannot hide an unresolved
semantic overlap.

Verdict: **VERIFIED WITH CAVEATS** for the contradiction-reconciliation
milestone. `CROSS-001 / H1A0-04` remains PARTIAL. The workbook was not edited,
and no subsequent milestone was started.

## 2026-07-22 - R0 H1A0 Defect Contract Verification

~~~text
cd D:\TrendForge\backend
python -m pytest tests\test_source_inventory_compiler.py -q
  18 passed in 4.81s
python -m pytest tests\test_api.py tests\test_surveillance_pledge_fpi.py tests\test_source_inventory_compiler.py tests\test_source_contract_hardening.py tests\test_safety_engine.py tests\test_market_context.py -q
  114 passed in 31.66s
python -m pytest -q
  523 passed in 100.73s
python -m compileall -q trendforge_api tests
python -m ruff check trendforge_api\source_inventory_compiler.py tests\test_source_inventory_compiler.py
python -m ruff format --check trendforge_api\source_inventory_compiler.py tests\test_source_inventory_compiler.py
  passed; 2 touched files formatted

cd D:\TrendForge
python docs\fable\remaining_build\build_coverage_csv.py --check
  Rows: 144; added=[]; removed=[]; changed=[]
  P0 build rows=42; P0 not implemented=49
~~~

Observed compiler/API result:

~~~text
workbook rows / normalized endpoints              370 / 351
normalized source contracts                             317
exact URL duplicate groups                               17
unexplained semantic overlaps                            32
raw key-prefixed / JSON-key-array defects           29 / 16
raw compound / sentinel defects                       2 / 4
non-data reference rows                                  42
lineage rows                                             370
H1A0 checks passed                                     5 / 6
unresolved contracts                                    317
source activation ready                               false
~~~

Fixtures prove duplicate URLs and unexplained multi-contract endpoints are
separate defects; an explicit overlap resolution clears only the overlap;
key-prefixed rows merge by retained key; reference rows remain quarantined;
all 11 Hybrid codes are present even at zero count; missing/empty inventories
fail closed.

Audit verdict: **PASS WITH CAVEATS**. `TDG-GAP-012` is verified at the
read-only compiler/API ceiling. `CROSS-001` remains partial because check 4
fails on 32 unresolved overlaps. The workbook was not edited, no source was
activated and no production readiness is claimed. Frontend validation is N/A
because it does not consume this route. Full mypy and repository-wide formatting
were not rerun; previously recorded unrelated debt was unchanged.

## 2026-07-22 - R0 Compiler-Gate Remediation Verification

The adversarial test target was precise: fresh structured parser output must
not become `PASS/CAN_CONFIRM` while compiler activation or per-contract gate
permission is absent.

~~~text
cd D:\TrendForge\backend
python -m pytest <5 focused compiler-gate tests> -q
  5 passed in 7.96s

python -m pytest tests\test_api.py tests\test_surveillance_pledge_fpi.py tests\test_source_inventory_compiler.py tests\test_source_contract_hardening.py tests\test_safety_engine.py tests\test_market_context.py -q
  109 passed in 32.85s

python -m pytest -q
  518 passed in 131.91s

python -m compileall -q trendforge_api tests
python -m ruff check <5 touched Python files>
python -m ruff format --check <5 touched Python files>
  passed; 5 files formatted

cd D:\TrendForge\frontend
npm test
  135/135 checks passed

cd D:\TrendForge
python docs\fable\remaining_build\build_coverage_csv.py --check
  Rows: 144; added=[]; removed=[]; changed=[]
  P0 build rows=43; P0 not implemented=50
~~~

Observed behavior:

- compiler activation is false and the compiled gate-authorized count is zero;
- fresh structured evidence returns `WAIT_SOURCE_ACTIVATION`, not `PASS`;
- every normal gate effect remains `DO_NOT_PASS_READY`;
- an ASM/GSM-listed symbol and an F&O-ban-listed symbol still receive their
  hard veto state;
- valid-empty and populated parser output remain distinguishable from fetch,
  schema, stale and parse failures;
- delayed CFTC rows remain queryable, but their context state cannot bypass
  source activation;
- all source-replacement-map rows are non-authoritative.

Coverage corrections are evidence, not implementation: `CROSS-001` and
`TDG-GAP-011` remain `PARTIAL`; `CROSS-020` is assigned to R1. Full mypy and
repository-wide Ruff formatting were not rerun in this remediation; the debt
recorded in the superseded snapshot below remains unresolved. No dependency,
database migration, workbook edit, deployment, broker access or trading action
occurred.

## 2026-07-22 - Superseded Initial R0 Inventory Verification

This retained snapshot predates the compiler-gate adversarial finding. Its
runtime measurements and test output remain historical evidence, but its
claims that `CROSS-001` and `TDG-GAP-011` were closed are superseded above.

### Commands and observed results

~~~text
cd D:\TrendForge\backend
python -m pytest -q tests\test_safety_engine.py tests\test_institutional_screener.py tests\test_q5_pk_compatibility.py tests\test_api.py tests\test_source_inventory_compiler.py
  132 passed in 191.47s

python -m pytest -q
  518 passed in 120.61s

python -m compileall -q trendforge_api tests
  passed

python -m ruff check trendforge_api tests
  All checks passed

python -m ruff format --check <10 touched Python files>
  10 files already formatted

python -m ruff format --check trendforge_api tests
  17 files would be reformatted; 147 files already formatted

python -m mypy trendforge_api tests
  324 errors in 42 files (164 source files checked)

cd D:\TrendForge\frontend
npm test
  135/135 checks passed

cd D:\TrendForge
python docs\fable\remaining_build\build_coverage_csv.py --check
  Rows: 144; added=[]; removed=[]; changed=[]
  P0 build rows=42; P0 not implemented=49

python -m compileall -q docs\fable\remaining_build\build_coverage_csv.py
  passed
~~~

The first complete backend run after removing executable quantity exposed four
failures: two obsolete quantity assertions, one institutional-direction
coupling defect and one load-sensitive PK worker timeout. The assertions were
updated to the approved no-quantity contract. Evidence direction was separated
from sizing, hard safety-lock precedence was restored, and the finite PK worker
default was raised from two to ten seconds. The final complete suite above is
the post-fix result.

### Runtime observations

Fresh `TestClient` observation used a temporary SQLite database and returned:

~~~text
GET /api/source-inventory/compiler-report       HTTP 200
compiler state                                  OK
workbook rows / canonical inputs                370 / 354
normalized endpoints / source contracts         351 / 317
sentinel status rows / lineage rows              4 / 370
H1A0 normalized acceptance                      5 / 6 (current reproduced result)
unresolved source contracts                     317
source activation ready                         false

GET /api/source-contracts/coverage             HTTP 200
inventory / classified / unclassified           351 / 351 / 0
contracted / gate-authorized sources             317 / 0
pending live verification                       317
source activation ready                         false

POST /api/risk/position-size                    HTTP 200
normal state                                    POSTPONED_NO_QUANTITY
normal executable / quantity                    false / 0
panic-lock state                                LOCKED_NO_TRADE
panic executable / quantity                     false / 0
~~~

### Honest limitations

- This historical section previously reported H1A0 as 6/6. Reproduction proves
  5/6 because 32 semantic overlaps remain; no source became usable.
- All 317 compiled contracts are unresolved and none can unlock a decision gate.
- Full mypy is not clean. Missing stubs and pre-existing type errors were not
  hidden or bypassed; installing stubs requires separate approval.
- Repository-wide Ruff formatting is not clean in 17 unrelated files. Touched
  files pass formatting and unrelated files were not mechanically rewritten.
- No UI behavior changed in this vertical, so browser screenshot claims were
  not added. The complete frontend contract suite passed.
- No dependency installation, database migration, workbook edit, broker access,
  deployment or trading action occurred.

## 2026-07-20 - DAT-010 / DAT-011 Feature Governance Verification

### Commands and observed results

~~~text
cd D:\TrendForge\backend
python -m pytest -q tests/test_feature_registry.py tests/test_institutional_screener.py tests/test_q5_family_resolver.py tests/test_q5_selection_contracts.py tests/test_q5_r2_fixtures.py tests/test_q5_r3_structure.py tests/test_q5_r4_enrichment.py tests/test_q5_r6_history_validation.py tests/test_api.py
  126 passed in 12.02s

python -m pytest -q
  514 passed in 73.04s

cd D:\TrendForge\frontend
cmd /c npm test
  135/135 checks passed

cd D:\TrendForge\backend
python -m compileall -q trendforge_api tests
  passed

python -m ruff check <touched feature/selection modules and tests>
  All checks passed

python -m ruff format --check <touched feature/selection modules and tests>
  passed

cd D:\TrendForge
python docs\fable\remaining_build\build_coverage_csv.py --check
  Rows: 144; added=[]; removed=[]; changed=[]
~~~

### Runtime observations

- Registry enumeration returned 39 unique IDs from `FTR-001` through
  `FTR-039`; lint returned `ok=true` with no errors.
- `GET /api/v1/selection/feature-registry` returned 200, 39 contracts,
  `researchOnly=true`, and `canUnlockConfirmed=false`.
- `GET /api/v1/selection/feature-registry/lint` returned 200 and validated all
  39 rows. POST, PUT and DELETE against the registry boundary returned 405.
- Route-aware lint left only FTR-013 and FTR-018 as `RESEARCH_ACTIVE`; an
  implementation module or HTTP 200 did not activate any other feature.
- Adversarial tests now reject unregistered claims, caller-controlled warm-up,
  duplicate/partial/unordered/mixed bars, non-finite vectors, engine drift,
  mixed per-run engines, false active routes, forged counts and forged run IDs.
- Successful empty parity input is not treated as proof; it returns an explicit
  invalid/incomplete result. Runtime version and parity divergence fail closed.

### Honest limitations

A focused mypy run that followed imported modules reported 53 errors in 10
modules. These include missing pandas stubs and existing type defects in
imported source-contract and selection modules. Ruff and runtime tests pass,
but **mypy is not clean**. No stub/dependency installation was performed because
that requires separate approval.

This verifies only the R0 feature/indicator contract ceiling. It is not
live-source verification, production authorization, a `CONFIRMED` unlock, or a
production-readiness claim.

## 2026-07-20 - R0 F&O-Ban / MWPL Split Verification

### Commands and observed results

~~~text
cd D:\TrendForge\backend
python -m pytest -q
  487 passed in 83.80s

cd D:\TrendForge\frontend
cmd /c npm test
  135/135 checks passed

cd D:\TrendForge\backend
python -m ruff check trendforge_api tests/test_source_contract_hardening.py tests/test_source_inventory_compiler.py tests/test_api.py
  All checks passed

python -m ruff format --check <14 changed backend/test files>
  14 files already formatted

python -m compileall -q trendforge_api tests
  passed

cd D:\TrendForge
python docs\fable\remaining_build\build_coverage_csv.py --check
  Rows: 137; added=[]; removed=[]; changed=[]
  P0 build rows=46; P0 not implemented=53
~~~

### Observed contract behavior

- F&O-ban parser accepts the official ban schema and rejects an MWPL percentage
  table as `WAIT_SCHEMA_MISMATCH`.
- MWPL-percentage parser accepts a schema-valid percentage table and rejects the
  ban artifact as `WAIT_SCHEMA_MISMATCH`.
- A valid-empty official ban artifact passes only the ban contract.
- Fresh valid-empty ban plus fresh FO evidence, with no percentage artifact,
  returns `WAIT_MWPL_PERCENTAGES` and cannot confirm.
- A listed symbol returns `BLOCKED_FNO_BAN`.
- The legacy `nse_mwpl_ban` key is absent from the active catalog and resolves
  only to the canonical ban descriptor for compatibility.
- Direct candidates contain the verified `fo_secban.csv` URL for
  `nse_fno_ban`; `nse_mwpl_percentages` has no guessed artifact URL.

### Not claimed

- Live symbol-level MWPL percentage availability.
- Universal tradability completion beyond CROSS-008.
- Production CONFIRMED, execution, quantity sizing or broker authority.
## 2026-07-20 - R0 Inventory Compiler Offline Verification

Historical snapshot: the current 2026-07-22 section at the top of this file
supersedes this section's compiler acceptance result.

### Commands and observed results

~~~text
cd D:\TrendForge
$env:PYTHONPATH='D:\TrendForge\backend'
python -m pytest backend/tests/test_source_inventory_compiler.py -q
  9 passed

python docs\fable\remaining_build\build_coverage_csv.py --check
  (after --accept-reviewed-changes) Rows: 137; added=[]; removed=[]; changed=[]
~~~

### Observed compiler behavior (workbook present)

- Loads `data/reports/SOURCE_LINK_INVENTORY_MASTER.xlsx` MASTER_CURRENT rows.
- Emits recomputed `rowCount`, `workbookSha256`, role counts, defect counts.
- Exposes 14 decision jobs (J01Ã¢â‚¬â€œJ14) and 10 maturity ladder stages.
- Declares ban/MWPL and FBIL/live FX contract splits without enabling execution.
- H1A0 acceptance total=6 and did not all pass on 2026-07-20. The current
  reproduced result is 5/6; check 4 remains open while raw defects stay visible.
- API `GET /api/source-inventory/compiler-report` returns camelCase research-only payload.
- API `GET /api/source-inventory/decision-jobs` returns taxonomy with `researchOnly=true`.

### Not claimed

- Live-source verification of every URL.
- Zero inventory defects.
- Production-ready or GATE_AUTHORIZED promotion.
- Quantity, OMS, or OpenAlgo execution.

## 2026-07-20 - Remaining-Build Repair Verification

The remaining-build governance pack and coverage generator were verified after
in-place repair. No new plan or replacement inventory was introduced.

### Commands and observed results

~~~text
cd D:\TrendForge
python -m py_compile docs\fable\remaining_build\build_coverage_csv.py
python docs\fable\remaining_build\build_coverage_csv.py --check
  Rows: 137; added=[]; removed=[]; changed=[]

cd D:\TrendForge\backend
python -m pytest -q
  474 passed in 80.82s

cd D:\TrendForge\frontend
npm test
  135/135 checks passed
~~~

Coverage integrity observed after regeneration:

~~~text
rows                                      137
unique requirement IDs                    137
blank last_verified fields                  0
blank reason fields                         0
P0 PLANNED or PARTIAL rows                 47
P0 rows not IMPLEMENTED                    56
temporary generator files                   0
~~~

Adversarial generator checks were performed without modifying the authoritative
CSV. Earlier checks rejected duplicate IDs, unknown columns, malformed dates,
whitespace IDs, unsupported IDs, and nonexistent tests. The final in-memory
suite also rejected deletion of a required HYBRID row, an unmanifested added
row, a future verification date, a fake code reference, a fake runtime route,
and an added row without explicit review acceptance. The same added row was
allowed only when review acceptance was true. Two independent Fable attacker
reviews then returned `VERIFIED`: one for the complete manifest/evidence guards and
one for authority, research-only scope, and exact File A roadmap alignment.

Contradiction searches found none of the repaired active defects: the old
`setdefault("last_verified", ...)` bug, canonical authority claim in the AI
advisory, `present.md` as current build order, the malformed CROSS range,
zero-quantity research-note wording, or the old universal
`evidence_level >= OBSERVED_RUNTIME` completion rule. Remaining `READY` and
zero-quantity text is preserved historical/advisory evidence or an explicit
rejection/mapping rule; it does not override the current research-only contract.

Acceptance ceiling: this proves documentation and generator consistency plus
current regression stability. It does not prove unfinished Q5/R behavior,
source freshness, live-feed reliability, execution safety, or production
readiness.

## 2026-07-20 - Merge-Plan Completeness Audit (Observed Proof)

Audit of `docs/fable/new_merge_PLAN_2026-07-18.md` against implementation.
Status narrative: `docs/BUILD_STATUS.md` (same date).
Full requirement matrix:
`docs/fable/remaining_build/INDEPENDENT_AUDIT_merge_plan_build_matrix_2026-07-20.md`.

### Commands and results

~~~text
cd D:\TrendForge\backend
python -m pytest tests/test_q5_selection_contracts.py
  tests/test_q5_family_resolver.py
  tests/test_q5_closed_bar_structure.py
  tests/test_q5_bounded_enrichment.py
  tests/test_q5_pk_compatibility.py
  tests/test_q5_history_validation.py
  tests/test_q5_openalgo_boundary.py -q
                                                      158 passed in 27.50s

cd D:\TrendForge\frontend
npm test                                              135/135 checks passed
~~~

Test module counts (backend Q5-focused):

~~~text
test_q5_selection_contracts.py                          10
test_q5_family_resolver.py                              10
test_q5_closed_bar_structure.py                         14
test_q5_bounded_enrichment.py                           27
test_q5_pk_compatibility.py                             31
test_q5_history_validation.py                           48
test_q5_openalgo_boundary.py                            18
sum                                                    158

~~~

### Observed in-process API contracts

~~~text
GET /api/v1/selection/fixtures/q5-r1                 HTTP 200
  milestone=Q5-R1
  acceptanceCeiling=NO_EARLY_CONFIRMED

GET /api/v1/selection/fixtures/q5-r2                 HTTP 200
  milestone=Q5-R2
  acceptanceCeiling=WATCH_WAIT_REJECT_ONLY

GET /api/v1/selection/fixtures/q5-r3                 HTTP 200
  milestone=Q5-R3
  fixtureOnly=true productionAuthorized=false executable=false
  acceptanceCeiling=EOD_CLOSED_BAR_RESEARCH_ONLY
  decision states include WATCH WAIT CONFIRMED REJECT

GET /api/v1/selection/fixtures/q5-r4                 HTTP 200
  milestone=Q5-R4
  fixtureOnly=true productionAuthorized=false executable=false
  acceptanceCeiling=UNKNOWN_EXPLICIT_NO_MCX_CONFIRMED

GET /api/v1/selection/fixtures/q5-r6                 HTTP 200
  milestone=Q5-R6
  fixtureOnly=true productionAuthorized=false executable=false
  acceptanceCeiling=NO_PERFORMANCE_OR_PROBABILITY_UI
  radar_states include REJECT

GET /api/v1/integrations/openalgo/capability         HTTP 200
  milestone=Q5-R7
  acceptanceCeiling=NO_INTRADAY_CONFIRMED
  state=ABSENT
  intradayConfirmationAllowed=false
  accountAccessAllowed=false executable=false
  productionAuthorized=false
~~~

### Five-point acceptance method applied

For each accepted Q5 requirement the audit required:

1. Code exists in the expected module.
2. It is connected to runtime (API route, intentional CLI, or documented freeze).
3. Output reaches the correct API/UI surface.
4. Failure and stale/closed-bar behavior is covered by tests.
5. Runtime behavior was observed (HTTP fixture/capability + FE acceptance), not
   merely mocked class construction.

A feature was **not** marked IMPLEMENTED when only a class name, empty route
stub, fixture label or HTTP 200 without adversarial behavior existed.

### What this audit proved

- Q5-R0Ã¢â‚¬Â¦Q5-R7 exist at their research/fixture ceilings and respond honestly.
- Family resolver, closed-bar structure, enrichment/MCX/options gates, offline
  PK harness, inspector/history/PIT contracts and OpenAlgo disabled boundary are
  covered by focused tests.
- Frontend primary radar (eight questions), hidden inspector, history labeling
  and validation lock pass acceptance (135/135).
- Production authorization remains false; performance/probability UI remains
  locked for fixture payloads; OpenAlgo does not unlock intraday CONFIRMED.

### What this audit did not prove

- Full-plan residuals in R0Ã¢â‚¬â€œR2, R4, R6 and product verticals R8Ã¢â‚¬â€œR18.
- Durable selection-state/PIT persistence (no migration).
- Live universe production selection scans.
- Live OpenAlgo feed, stream integrity or SHADOW_LIVE continuity.
- Scanner Lab UI, pipe DSL or full native PK catalog.
- Browser screenshot QA (not rerun in this audit).
- 1:1 named pytest for every plan ID `T-001..T-110` / `T-170+` (many are
  PARTIAL via related suites; PK offline T-191/192/193 are strong).

### Completeness claim

~~~text
Q5-R0..Q5-R7 at approved ceilings                         PROVEN
Entire merge-plan document requirement-complete           NOT PROVEN
Production-ready claim                                    NOT MADE
~~~

## 2026-07-20 - Q5-R6 Repair And Q5-R7 Boundary Validation

Commands and observed results:

~~~text
cd D:\TrendForge\backend
python -m pytest tests\test_q5_history_validation.py
  tests\test_q5_openalgo_boundary.py tests\test_openalgo_client.py
  tests\test_openalgo_ohlcv_adapter.py -q                   77 passed
python -m pytest tests\test_q5_openalgo_boundary.py
  tests\test_openalgo_client.py tests\test_openalgo_ohlcv_adapter.py -q
                                                               29 passed
python -m pytest -q                                          474 passed

cd D:\TrendForge\frontend
node --check q5-contract.js                                  passed
node --check app.js                                          passed
npm test                                                    135/135
~~~

Observed in-process API contracts:

~~~text
GET /api/v1/selection/fixtures/q5-r6                     HTTP 200
milestone                                                    Q5-R6
fixtureOnly / productionAuthorized                    true / false
outcomes key serialized                                        false
performance/probability UI                              false/false

GET /api/v1/integrations/openalgo/capability            HTTP 200
milestone                                                    Q5-R7
acceptanceCeiling                           NO_INTRADAY_CONFIRMED
state                                                        ABSENT
enabled/configured                                     false/false
forbiddenRoutesPresent                                          []
intradayConfirmationAllowed                                  false
accountAccessAllowed / executable                      false/false
productionAuthorized                                        false
~~~

Adversarial behaviors now covered:

- Direct WATCH-to-CONFIRMED is denied and routed through WAIT. CONFIRMED derives
  proof from closed-bar identity, official PIT facts, independent evidence
  families and passed gates; fabricated proof fields fail validation.
- State-event diffs are sorted before identity, REJECT is terminal for one
  candidate instance, and reopen behavior requires a new linked instance.
- Target/stop/censored/no-entry labels, returns, MFE/MAE and availability derive
  from immutable closed bars. Rewriting cost, label or return fails validation.
- A genuine no-entry path has zero performance and zero transaction cost.
- Public fixture serialization excludes internal entry/target/stop paths.
- Walk-forward and holdout approval requires available, hashed, versioned
  artifacts bound to the exact outcome IDs. Missing, failed, future or mismatched
  artifacts reject PIT.
- Drift status requires a hashed artifact tied to the approved validation run
  and baseline/current windows. Missing or mismatched artifacts demote; drift
  never auto-promotes.
- Unknown frontend states and malformed Q5 payloads fail closed to WAIT. WATCH
  and WAIT have distinct filters. Eight questions render in the primary
  candidate area; validation remains hidden for fixture or unauthorized data.
- OpenAlgo is disabled by default, rejects remote/write/account boundaries,
  exposes no secret, and cannot unlock intraday CONFIRMED in any currently
  tested state.

Caveats:

- Q5-R6 remains fixture-only. No production dataset, probability/performance
  authorization or durable history/PIT persistence was validated.
- Q5-R7 observed `ABSENT`, not a live broker feed. Live-shadow continuity and
  replay integrity are unverified, so intraday CONFIRMED remains unavailable.
- No browser screenshot run was performed in this repair. Frontend verification
  is syntax, pure contract behavior and DOM acceptance coverage.

## 2026-07-19 - Q5-R6 Inspector, History And PIT Governance Validation

Commands and observed results:

~~~text
cd D:\TrendForge\backend
python -m pytest tests\test_q5_history_validation.py -q      48 passed
python -m pytest -q                                         456 passed
python -m ruff check trendforge_api\selection
  trendforge_api\main.py tests\test_q5_history_validation.py
                                                     all checks passed
python -m ruff format --check trendforge_api\selection
  tests\test_q5_history_validation.py                 14 files formatted

cd D:\TrendForge\frontend
node --check app.js                                           passed
node --check tests\acceptance-check.js                        passed
npm test                                                    133/133

GET http://127.0.0.1:8001/api/v1/selection/fixtures/q5-r6   HTTP 200
~~~

Observed live contract:

~~~text
milestone                               Q5-R6
acceptance ceiling       NO_PERFORMANCE_OR_PROBABILITY_UI
fixtureOnly / productionAuthorized      true / false
executable                                    false
radar state                                  REJECT
history current state                        REJECT
inspector state                              REJECT
performance/probability visible        false / false
validation section                           HIDDEN
outcome observations                              4
~~~

Focused adversarial coverage proves:

- CONFIRMED is denied without a complete proof envelope and recoverable
  confirmation failure becomes WAIT, including WATCH-to-confirm attempts.
- State events retain material claim/gate/source diffs, remain unique and
  reconstruct a contiguous candidate history.
- Successful right-censor, non-entry, invalidation, delisting/unpriced and
  incomplete-data states are distinguishable from resolved target/stop paths.
- Only resolved entered paths count toward performance metrics; non-entry and
  censored rows cannot inflate the effective sample.
- Costs and net returns are recomputed against the versioned cost profile;
  forged arithmetic, future cost profiles and unavailable outcomes fail PIT.
- Calibration, drawdown, false-confirmed rate and sensitivity are derived from
  outcomes. Missing walk-forward/holdout artifacts or failed gates reject PIT.
- Drift cannot predate its baseline, cannot auto-promote and demotes on missing,
  invalid or excessive values.
- Inspector sections, source-health rows and selected/suppressed/opposing claim
  roles are unique; radar, history and inspector state must agree.
- The API DTO contains no trade direction, entry, stop, target, quantity, order
  intent or win-probability contract.
- Frontend acceptance checks all `getElementById` references against real HTML
  IDs, hides the fixture validation tab, renders history, uses exactly the four
  public selection states and fails Q5 loading closed to WAIT.

The in-app browser runtime failed twice before navigation with a Windows sandbox
setup error, so screenshot and interactive-tab evidence is not claimed. This is
a verification caveat, not a hidden pass. The live API and static frontend
contract both passed. No production PIT dataset, persistent state-history store,
probability/performance authorization or execution path was validated.
## 2026-07-19 - Q5-R5 Offline PK Compatibility Validation

Commands and observed results:

~~~text
python -m pytest tests/test_q5_pk_compatibility.py -q          31 passed
python -m pytest <all five Q5 test modules> -q                92 passed
python -m pytest -q                                          408 passed
python -m ruff check .                                all checks passed
python -m ruff format --check trendforge_api/scanners
  tests/test_q5_pk_compatibility.py                            passed
python -m compileall -q trendforge_api tests                   passed
cd ../frontend && npm test                                   119/119
python -m trendforge_api.scanners                              passed
PK/shadow production route inventory                         0 routes
~~~

Observed fixture results:

~~~text
successful differential                                  MATCH
second differential                                 UNRESOLVED
fixtureOnly                                                true
upstreamObserved                                          false
fixture promotion                         REGISTERED_NOT_ACTIVE
shadow votingWeight                                         0.0
shadow rank/state/confirm authority            false/false/false
productionAuthorized / executable                  false / false
worker invocations per run                                     1
finiteProcessTerminated                                  true
~~~

The 31 focused tests verify strict pins and hashes, safe JSON-only manifests,
path rejection, stable identity, schema and normalized-input validation,
explicit fixture/upstream provenance, zero-authority shadow observations,
one-shot bounded process execution, timeout/crash/non-JSON/oversized-output
failure states, reviewer consistency, native-only promotion blockers and the
absence of production PK routes. Successful match output is never used as a
replacement for process or parse failure.

Repository-wide `python -m ruff format --check .` remains non-green because 20
unrelated pre-existing files would be reformatted. The five Q5-R5 touched files
are formatted. This milestone proves only the finite offline fixture contract;
it does not prove PKScreener parity, source validity, production readiness or
trading performance. No database migration was required.
## 2026-07-19 - Q5-R2 Family Resolver Validation

Commands and observed results:

```text
python -m pytest tests/test_q5_family_resolver.py -q           10 passed
python -m pytest tests/test_q5_selection_contracts.py
  tests/test_q5_family_resolver.py -q                         20 passed
python -m pytest -q                                           336 passed
python -m ruff check trendforge_api/source_contracts.py
  trendforge_api/selection tests/test_q5_selection_contracts.py
  tests/test_q5_family_resolver.py                      all checks passed
python -m compileall -q trendforge_api                           passed
cd ..\frontend && npm test                                    119/119
GET /api/v1/selection/fixtures/q5-r2                           HTTP 200
```

Observed fixture results:

```text
TF_WATCH                 WATCH   one activity vote; duplicate/shadow suppressed
TF_WAIT_CLOSE            WAIT    open-bar and missing-participation gates
TF_WAIT_EARLY_CONFIRM    WAIT    Q5-R2 no-CONFIRMED ceiling
TF_REJECT                REJECT  hard safety veto only
corroboration bonus      0.0     for every resolution
```

The focused suite proves input-order determinism, one selected claim per
correlation-group side, stronger shadow exclusion, future-claim exclusion,
visible opposition subtraction, valid-empty source acceptance, blocked-source
WAIT behavior, partial-scan WAIT behavior and hard-veto REJECT behavior. The
API contains no trade direction, entry, stop, target, quantity, order intent or
win-probability fields.

This milestone does not calibrate a confirmation threshold and does not claim
production readiness. No database migration or live-source fetch was required.


## 2026-07-19 - Q5-R1 Source, Identity And PIT Fixture Validation

Commands and observed results:

```text
python -m pytest tests/test_q5_selection_contracts.py -q       10 passed
python -m pytest -q                                           326 passed
python -m ruff check trendforge_api/source_contracts.py
  trendforge_api/selection tests/test_q5_selection_contracts.py
                                                        all checks passed
python -m compileall -q trendforge_api                           passed
cd ..\frontend && npm test                                      passed
GET /api/v1/selection/fixtures/q5-r1                           HTTP 200
```

The observed API payload reported:

```text
milestone                                           Q5-R1
acceptance ceiling                      NO_EARLY_CONFIRMED
public state schema              WATCH WAIT CONFIRMED REJECT
emitted fixture states                 WATCH WAIT REJECT
candidate count                                      4
source result states       STRUCTURED_OK VALID_EMPTY BLOCKED
CONFIRMED fixture candidate                       false
tradeDirection/entry/stop/target fields           absent
quantity/orderIntent/winProbability fields        absent
```

Focused tests prove:

- `VALID_EMPTY` differs from blocked/fetch failure and requires dated artifact
  proof plus contract-defined empty semantics.
- A raw HTTP artifact without parser/schema/date proof remains `PARTIAL`, even
  when the transport succeeded.
- Point-in-time timestamps must be timezone-aware and a fact available after
  the decision time is ineligible for that decision.
- Stable identity generation is deterministic and event business-key ordering
  cannot change the event ID.
- WAIT requires a named blocking gate, REJECT requires a deterministic reject
  gate, and a synthetic/demo candidate cannot become CONFIRMED.
- The four public states remain in the schema while the Q5-R1 milestone ceiling
  prevents any CONFIRMED fixture output.

No database migration or live-source fetch was required for this fixture and
contract milestone. The older causal engine and dashboard demo are explicitly
outside this additive Q5-R1 acceptance; Q5-R2 owns resolver behavior.


## 2026-07-19 - Q5-R0 Contract Freeze

Deterministic Q5-R0 verification passed:

```text
TRC-056 immutable audit fingerprint        PASS (875 lines, exact SHA-256)
PK-019 / API-019 / FUS-011                 PASS
STA-007 / DOC-ERR-001 / TRC-056            PASS
Q5-R0 documentation-only ceiling           PASS
PK finite offline/no-sidecar boundary      PASS
FUS zero corroboration bonus               PASS
STA recoverable WAIT/hard-veto REJECT      PASS
DOC bar_versions erratum                   PASS
TRC audit range coverage 1-875             PASS
production PK shadow route absent          PASS
```

Recovered artifact:

```text
docs/fable/INDEPENDENT_AUDIT_new_merge_PLAN_2026-07-18.md
lines    875
bytes    44303
SHA-256  8355D2C129037505DD2D32773E5B643EDCE5BE7DB9F7B4EFA33256105895D6C7
```

The bytes were reconstructed from four complete numbered read results in the
local prior-session record. Candidate encodings and line endings were checked
in memory; only UTF-8 without BOM, LF endings and a final newline matched the
authoritative fingerprint. The destination was written only after that match
and was hash-checked again afterward.

Q5-R0 is verified as documentation and contract work only. It does not claim
runtime implementation or production readiness. No dependency, database
migration, external write, broker access, deployment or trading action occurred.

## 2026-07-19 - Q5 Baseline Runtime Hardening

The three previously observed failures were reproduced before editing:

```text
test_scanner_attaches_normalized_cause_and_sponsor_claims           failed
test_retry_after_is_bounded_and_success_reports_attempts            failed
test_html_access_denied_is_wrong_content_not_valid_empty            failed
```

Post-fix observations:

```text
python -m pytest <three focused node IDs> -q                       3 passed
python -m pytest test_source_runtime_hardening.py
  test_evidence_builder.py test_institutional_screener.py
  test_corporate_disclosure_fetch.py
  test_extended_market_sources.py -q                             36 passed
python -m pytest -q                                             316 passed
python -m ruff check trendforge_api tests tools           all checks passed
python -m compileall -q trendforge_api tests tools                 passed
npm test                                                        119/119
node --check app.js                                                passed
```

The focused tests observed these contracts:

- HTTP 429 honors bounded `Retry-After`, retries, and reports two attempts plus
  the final HTTP status.
- HTTP 200 access-denied/CAPTCHA HTML is `WRONG_CONTENT` with
  `errorType=BLOCK_PAGE`, zero records and `canScore=false`.
- Fresh point-in-time CAUSE/SPONSOR fixture evidence remains deterministic while
  production evidence still uses normal staleness decay.

Repository-wide caveats observed in the same run:

```text
python -m ruff format --check trendforge_api tests tools
  21 files would be reformatted; this includes untouched pre-existing files

python -m mypy trendforge_api
  72 errors in 14 files; includes missing third-party stubs and existing
  OpenAlgo, market-activity, intraday-detail and commodity-context typing debt
```

Initial Q5-R0 preflight observations:

```text
PK-019 / API-019 / FUS-011 / STA-007 present with final authority
DOC-ERR-001                              bar_versions correction present
production PK shadow route              absent
TRC-056 audit file                      missing
project/attachment SHA-256 match        none
```

At that preflight, the closest available independent-review attachment had 852
lines and SHA-256
`728885746AB99DB67E32967402579D2EDDC5A0E0C4677AC18104E323777FB871`;
it was correctly rejected as a substitute for the recorded 875-line audit.
The later Q5-R0 entry above records exact recovery from prior session evidence.

No dependency was installed, no database migration was run, and no external,
broker, account, deployment or trading action occurred.

## 2026-07-17 - Twelve-Route Source Merge

Static verification passed:

```text
python -m py_compile institutional_config.py institutional_sources.py intraday_stock_details.py macro_event_context.py
pytest test_intraday_stock_details.py test_macro_event_sources.py test_institutional_screener.py -q
27 passed
```

Live fetch verification through `AsyncEndpointClient` passed for all twelve
routes: `12` fresh `RAW_ARCHIVED`, `0` broken, `0` stale fallback and `0`
wrong-content responses. The CFTC routes were rerun at 500 latest-first rows;
all stayed below the raw-response size guard.

Observed payload sizes:

```text
NSDL FPI daily report detail                 17 HTML tables
BSE SAST                                    37 rows
CFTC legacy/disaggregated/TFF              500 rows each
NSE shareholding pattern                    91 RELIANCE rows
NSE Nifty option/future                  1464 / 3 rows
NSE Bank Nifty option/future              993 / 3 rows
NSE most-active volume / volume gainers    20 / 25 rows
```

The saved screener snapshot had `sourceCompleteness=1.0`, twelve fresh sources,
one research candidate, and `RESEARCH_ONLY` state. RELIANCE displayed
`promoter_holding_pct=50.48`, `public_holding_pct=49.52`, and
`shareholding_date=30-JUN-2026`. This proves data arrival and guarded
research wiring, not trade validity or execution readiness.

Workbook serial verification:

```text
uniqueLinksInReports 354
uniqueLinksInWorkbook 354
missingFromWorkbook 0
extraInWorkbook 0
```

Updated: 2026-07-15

## 2026-07-15 Macro/Event Source Validation

Focused backend validation:

```powershell
cd D:\TrendForge\backend
python -m pytest tests/test_macro_event_sources.py tests/test_extended_market_sources.py tests/test_commodity_context.py -q
```

Result:

```text
17 passed in 4.76s
```

Post-change full backend regression:

```powershell
cd D:\TrendForge\backend
python -m compileall -q trendforge_api tests
python -m pytest -q
```

Result:

```text
compileall passed
306 passed in 63.06s
```

Live bounded macro/event fetch:

```text
snapshot_state=WAIT_PARTIAL_SOURCE
source_completeness=0.65
sources=20
connected/archived=13
fail_closed=7
canUnlockReady=false
endpoint_contracts=74
canonical_inventory_rows=233
fresh_structured_rows=45
not_fresh_structured_rows=188
```

Fail-closed live reasons:

```text
des_crop_estimates: TLS certificate verification failed locally
shfe_weekly_stock: tested dated .dat path returned 404
china_nbs_indicator: returned 403
mcx_future_prices: MCX seed returned 403
mcx_trading_holidays: MCX seed returned 403
mcx_circulars: MCX seed returned 403
nse_xbrl_taxonomy: tested page returned 404
```

## Baseline Commands

Backend:

```powershell
cd backend
python -m pytest -q
```

Result before current edits: `55 passed in 25.37s` using Python 3.14.3.

Frontend:

```powershell
cd frontend
npm test
```

Result before current frontend edits: `74/74` static acceptance checks passed.

Source-contract TDD:

```powershell
cd backend
python -m pytest -q tests/test_api.py -k "saved_link_inventory or source_contract_coverage"
```

Expected red phase: import failed because `source_registry_contracts` did not exist.

Implemented result: `2 passed, 55 deselected in 1.71s`.

## Post-Change Full Validation

```text
python -m pytest -q
94 passed in 25.36s

python -m ruff check trendforge_api tests
All checks passed

python -m ruff format --check trendforge_api tests
57 files already formatted

python -m mypy trendforge_api --ignore-missing-imports
Success: no issues found in 50 source files

python -m compileall -q trendforge_api tests
passed

npm test
81/81 checks passed

source coverage
209 inventory URLs
209 classified URLs
0 unclassified URLs
25 active source descriptors
25 active source contracts

python -m trendforge_api.cli init-db
integrity=ok, foreignKeys=true, journalMode=wal

python -m trendforge_api.cli demo-data --symbol TFDEMO
160 daily and 750 five-minute candles generated and saved
seven Parquet files written after derived-timeframe generation
trustLevel=SYNTHETIC_TEST, executable=false

demo derived series
30m=130, 1h=70, 4h_custom=20, 1d=10, 1w=3
all derived rows persisted to SQLite and seven total demo Parquet paths written

live runtime on http://127.0.0.1:8001/
health=ok, mode=guarded-research
source coverage=209 inventory / 209 classified / 0 unclassified
active contracts=25 / 25
browser console errors=0
body width=viewport width=1137 (no horizontal overflow)

POST /api/nse/resample for TFDEMO 5m -> 4h_custom
20 candles, 10 PARTIAL_NSE_SESSION, 0 warnings
```

## Causal Engine TDD

```powershell
cd backend
python -m pytest tests/test_causal_engine.py -q
```

Red phase: four regression tests failed for stale-weight capping, mandatory layer floors, duplicate evidence IDs and timezone-naive cutoffs.

Implemented result: `15 passed in 1.20s`.

Coverage includes classification requirements, MF delayed weight, exponential decay, point-in-time rejection, independence penalties, percentile ranking, Stage 1 blocking Stage 2, unofficial production downgrade, safety override, read-only READY, typed API aliases and duplicate-symbol rejection.

## Named-State Scanner Integration

```powershell
python -m pytest tests/test_decision_fixtures.py -q
python -m trendforge_api.cli demo-decisions
```

Result: `3 passed`. The CLI persisted run `6` with eight candidates: READY 1, WAIT 1, REJECT 2, NO_TRADE 1, WAIT_DATA_WEAK 1, WAIT_FOMO 1 and LOCKED_NO_TRADE 1. Every scenario is `SYNTHETIC_TEST` and `executable=false`.

Live API after restart on `http://127.0.0.1:8001/`:

```text
health=ok
latest run=6
latest candidates=8
shortlist=1
WAIT candidates=3
rejected/safety-block candidates=4
```

Browser validation rendered all eight scenario cards, including `WAIT_FOMO`, `LOCKED_NO_TRADE`, `REJECT`, `WAIT_DATA_WEAK` and `NO_TRADE`; console errors were zero and body width equaled the 1137px viewport.

## Migration And Candle Lineage

```powershell
python -m pytest tests/test_candle_lineage.py -q
python -m trendforge_api.cli migrate
python -m trendforge_api.cli demo-data --symbol TFDEMO
```

Focused result: `5 passed`. Full result after correcting an invalid legacy synthetic-candle fixture: `82 passed`.

The live migration command reported `PASS` with `0001_existing_baseline`, `0002_candle_quality_lineage` and `0003_normalized_evidence_claims`. Reloading unchanged TFDEMO data saved zero new candles, produced zero revisions and retained 1,143 deduplicated quality records. All TFDEMO quality rows are WARN because the source is deliberately `SYNTHETIC_TEST`, not because their OHLC geometry failed.

## Normalized Evidence Claims

```powershell
python -m pytest tests/test_evidence_builder.py -q
```

Result: `4 passed`. Controlled structured rows produced six claims across CAUSE and SPONSOR, excluded ESOP and future-observed rows, persisted without duplicates, and appeared inside the scanner candidate causal evaluation. The scanner remained non-READY because official source-readiness confirmation was intentionally absent.

Live `GET /api/evidence/TFDEMO` returned zero claims, which is the correct fail-closed result because no structured source rows are attached to the synthetic demo symbol.

## Harmonic Lifecycle

```powershell
python -m pytest tests/test_harmonic_lifecycle.py -q
python -m trendforge_api.cli demo-harmonic-lifecycle
```

Result: `4 passed`. Nine deterministic scenarios cover FORMING, COMPLETE, TRIGGERED, INVALIDATED, WIN_T1, WIN_T2, WIN_T3, LOSS and EXPIRED. Repeated fixture loading saved zero duplicate events. A same-bar target and invalidation resolves conservatively to LOSS.

The live CLI stored 20 ordered events. `GET /api/harmonic/lifecycle/events?patternKey=TF_LIFE_WIN_T3` returned three transitions ending in `WIN_T3`. Migration `0004_harmonic_lifecycle_events` is applied.

## Alerts And Journal

```powershell
python -m pytest tests/test_alerts_journal.py -q
```

Result: `4 passed`. Alerts persist reason and risk context, acknowledgement updates are durable, valid manual journal entries can be closed with P&L and R-multiple outcomes, and invalid stop geometry or broker-order fields return HTTP 422.

Live validation created one synthetic `HARMONIC_LOSS` alert and one closed synthetic TFLIFE journal record with `LOSS` and `-1R`. Migration `0005_alerts_and_manual_journal` is applied. No broker order was created or accepted.

Dashboard runtime validation loaded both persisted records without console errors. The alert acknowledgement control reduced the unacknowledged count from one to zero, and the journal form created a synthetic `TFUI` record in `WAIT_UI_TEST` with explicit no-broker notes. The list updated from one to two rows immediately. At the 390px responsive breakpoint, body width stayed within the viewport and the command bar, radar, analysis and proof regions each used the available mobile width.

## Scheduled Harmonic Lifecycle

```powershell
python -m pytest tests/test_scheduled_harmonic_lifecycle.py -q
python -m pytest tests/test_scheduled_harmonic_lifecycle.py tests/test_evidence_builder.py tests/test_harmonic_lifecycle.py tests/test_alerts_journal.py -q
```

Results: `3 passed` focused and `15 passed` across the connected lifecycle/evidence/alert slice. Tests prove stable XABCD-derived keys, COMPLETE to TRIGGERED to WIN progression, idempotent reruns, timezone failure, unpassed-pattern exclusion and fail-closed revised-sequence conflict.

The current-database runtime command completed scanner run `8` with two candidates. Both persisted a typed `harmonicLifecycle` payload and remained non-executable with official source gates blocked. No real stored series happened to contain a qualifying STRICT/NORMAL pattern in this smoke run; the deterministic integration fixtures prove the transition path.

Post-slice full validation:

```text
pytest: 97 passed in 25.94s
ruff check: all checks passed
ruff format --check: 59 files already formatted
mypy: no issues in 51 source files
compileall: passed
frontend: 81/81 checks passed
```

## Corporate-Action Integrity

```powershell
python -m pytest tests/test_corporate_action_integrity.py -q
python -m trendforge_api.cli migrate
```

Focused result: `8 passed`. Coverage includes ratio/revision parsing, official mirror agreement, ratio conflict, split/bonus price-volume adjustment, cash-dividend reference-close adjustment, rights TERP adjustment, non-adjusting buyback exclusion, unadjusted rejection, late-arriving action veto before harmonic analysis, persisted lineage, API contracts and explicit revision-ledger recovery.

Full result after dividend/rights integration: `105 passed in 27.40s`; Ruff lint passed, Ruff format reports 61 files formatted, mypy reports no issues in 52 source files, compileall passed, and frontend checks remain `81/81`.

The live database applied `0006_corporate_action_adjustment_lineage`. Scanner run `9` completed two research candidates with official source gates still blocked. Reloading TFDEMO persisted seven PASS assessments with zero known intersecting actions. The browser displayed `Corporate Actions: PASS` with the reason, zero console errors and no horizontal overflow. This does not prove live official corporate-action downloads; merger/demerger, reconstruction and ambiguous action terms remain fail-closed.

## Required Before Milestone Completion

```powershell
cd backend
python -m pytest -q
python -m ruff check trendforge_api tests
python -m ruff format --check trendforge_api tests
python -m mypy trendforge_api --ignore-missing-imports
python -m compileall -q trendforge_api tests
cd ..\frontend
npm test
```

Browser-console/responsive checks and database integrity must be rerun after later runtime/UI changes. Do not infer them from narrow tests.

## VYOM Dynamic Source Discovery - 2026-07-13

```text
VYOM API/security tests                         33 passed
TrendForge VYOM/source-hardening focused tests 11 passed
VYOM example.com smoke                         DISCOVERED, 1 link, canUnlockReady=false
NSE SLB parser after VYOM                      WAIT_EMPTY_PARSE, 0 rows
AMFI portfolio parser after VYOM               WAIT_EMPTY_PARSE, 0 rows
SEBI PIT/SAST parser after VYOM                 PARSED_METADATA_ONLY, 0 rows
MCX bhavcopy parser after VYOM                  WAIT_EMPTY_PARSE, 0 rows
Ruff focused check                              passed
Mypy focused check                              passed
```

The initial VYOM runtime failed on Windows `cp1252` logging. Forcing UTF-8 in
the isolated subprocess corrected the runtime. No VYOM output was accepted as
source evidence. Exact URLs, content hashes, attempt groups and outcomes are in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S015`.

Final milestone validation:

```text
backend pytest                 185 passed in 38.27s
ruff check                     passed
ruff format --check            93 files formatted
mypy                           70 source files, no issues
compileall                     passed
frontend acceptance            95/95 passed
runtime health                 ok on 127.0.0.1:8001
attempt ledger runtime query   2 NSE SLB rows returned
```

## Official NSE Buyback And BSE Offer XBRL

The official NSE daily-buyback endpoint was fetched and archived as a valid dated empty report. Snapshot SHA-256 was `8fe32e407a1038ee38753b70e5374b3a46d6ae9d5f16cd5b73c53abaca8f5ed0`; parser state was `PARSED_STRUCTURED`, record count zero, `validEmpty=true`, and source data date 2026-07-11.

The official BSE buyback and takeover APIs resolved 76 and 157 index rows respectively. Those index rows remain `PARSED_METADATA_ONLY`. Linked official XBRL detail parsing was proven with immutable local artifacts:

```text
TEAMLEASE SERVICES LIMITED buyback PRE terms
data date=2026-07-07, price=INR 1600, quantity=1,487,500
raw hash=64e0c478532b8a5163f39a52b04e0c1ce5bb5ba6d66f473a25f604b2d9440412

Senthil Infotek Limited takeover POST terms
data date=2026-07-08, price=INR 8, BSE scrip=531980
raw hash=70769a4572ba0419314a4c751ca81d30ab56a22afe65a052e4845ac3d5fadb21
```

The XBRL parser rejects malformed XML, DTD/entity declarations and incomplete mandatory terms. Revision history remains immutable while only the latest deterministic version is current. One current offer produces at most one contextual CAUSE claim; PRE terms are preferred over POST outcomes. Offer terms cannot supply sponsor proof or independently create `READY`.

```text
python -m pytest -q                         114 passed in 29.47s
python -m ruff check trendforge_api tests   all checks passed
python -m ruff format --check ...           65 files formatted
python -m mypy ... --ignore-missing-imports success, 55 source files
python -m compileall -q ...                 passed
npm test                                    83/83 passed
browser desktop/mobile                      0 console errors, 0 horizontal overflow
```

Migration `0007_bse_offer_xbrl_lineage` is applied. Full historical XBRL backfill, scheduled detail refresh and merger/demerger reconstruction remain unresolved.

## Merger And Demerger Reconstruction Guard

Migration `0008_corporate_reconstruction_terms` adds explicit price-adjustment factor, predecessor symbol, successor symbol and continuity-confirmation lineage to corporate events. Demerger classification is evaluated before merger classification so the substring cannot collapse the two event classes.

The model authorizes in-place reconstruction only when official terms contain a positive explicit factor and confirm that predecessor and successor are the same symbol. A share-exchange ratio alone is not a price factor. Cross-symbol schemes, missing terms and conflicting official factors remain `WAIT_DETAILS` or `CONFLICT`, causing `REJECT_DATA_INTEGRITY` before harmonics. An authorized factor adjusts historical OHLC but does not manufacture volume changes.

```text
focused corporate/migration tests  19 passed in 4.63s
full backend tests                 118 passed in 30.41s
Ruff lint                          all checks passed
Ruff format                        65 files formatted
mypy                               no issues in 55 source files
compileall                         passed
frontend                           83/83 passed
live migration                     8 versions, PASS
live health                        ok, guarded-research
browser reload                     0 warnings/errors, no horizontal overflow
```

This does not claim that cross-symbol merger histories are solved. Those require a separate instrument-identity lineage and multi-series reconstruction model; TrendForge continues to block them.

## Persisted Risk And Safety Orchestration

Migration `0009_safety_state_events` adds an audit ledger for panic, cooldown and recovery transitions. The safety engine derives the current Asia/Kolkata session state from persisted journal outcomes and active safety events. Defaults enforce one-loss and two-loss cooldowns, a three-loss lock, a 1% daily soft-risk reduction and a 1.5% daily hard lock for the INR 1,00,000 profile.

Position sizing now reads persisted settings and server-derived safety state. Confidence selects only an allowed risk tier; it cannot exceed stop-risk, total open-risk, sector, correlation, liquidity, margin, lot or MCX-position caps. `COOLDOWN_ACTIVE`, `WAIT_EMOTIONAL_RISK`, `LOCKED_NO_TRADE`, `STOP_TRADING_NOW` and broker-trauma states return zero quantity. The scanner stores the same `TRADER_SAFETY` gate and cannot bypass it.

```text
focused safety/risk/API tests  15 passed
full backend tests            123 passed in 35.07s
Ruff lint                     all checks passed
Ruff format                   67 files formatted
mypy                          no issues in 56 source files
compileall                    passed
frontend                      87/87 passed
live migration                9 versions, PASS
live safety API               GREEN, multiplier 1.0
browser desktop/mobile        0 warnings/errors, 0 horizontal overflow
```

The live dashboard reads `/api/safety/status`; its lock button calls the persisted panic API and recovery requires five checked acknowledgements plus elapsed cooldown. Validation deliberately did not activate panic mode in the user's live database. Automated broker execution remains absent.

## NSE Instrument Universe And Market/Sector Context

The official NSE equity master and Nifty 500 membership artifacts were fetched through the production resolver, archived by hash, parsed, normalized and joined point-in-time:

```text
EQUITY_L.csv
HTTP 200, 168,316 bytes
SHA-256 6b1a9adb38c92a3b61a085dfc8e7ccbb61c54ffe81d322e5c7293944495ed222
data date 2026-07-09, parser 1.0.1, 2,384 rows, STRUCTURED_OK/FRESH

ind_nifty500list.csv
HTTP 200, 32,766 bytes
SHA-256 f9938da0fd227cefece7451bd6b18d7aa4b39945a3f904d4aebda295fe2b3dda
data date 2026-07-11, parser 1.0.1, 500 rows, STRUCTURED_OK/FRESH
```

The first live equity parse exposed that generic extraction selected a constituent listing date instead of the file timestamp. Parser v1.0.1 now prioritizes HTTP `Last-Modified`; the 2,384 bad normalized rows remain in audit history with `active=0`, and the corrected 2026-07-09 rows are current.

The context engine covers 20/50/200-DMA trend state, VIX bands and 30% shock, advance/decline breadth, narrow-index divergence and four-state sector RRG. Future/stale context fails closed. Scanner tests prove missing context becomes `WAIT_DATA_WEAK`, VIX/breadth shock becomes `NO_TRADE`, and sector conflict cannot be rescued by setup quality.

```text
connected context/integrity tests 33 passed
full backend tests               129 passed in 41.90s
Ruff lint                        all checks passed
Ruff format                      70 files formatted
mypy                             no issues in 58 source files
compileall                       passed
frontend                         89/89 passed
live migrations                  11 versions, PASS
browser desktop/mobile           0 warnings/errors, 0 horizontal overflow
```

No live market snapshot was manufactured. The dashboard shows `WAIT_CONTEXT` and `WAIT_DATA` until dated Nifty, India VIX and breadth data are loaded.

## NSE Calendar And Scheduler Guard

The official NSE `holiday-master?type=trading` response was fetched through the source resolver, archived by SHA-256 and parsed into segment-specific closures plus annual coverage. Runtime evaluation uses Asia/Kolkata time. Covered weekdays with no closure are normal-open; published holidays and weekends are closed. A weekend can open only through an explicit `OPEN_SPECIAL` source record.

```text
live HTTP                              200, 33,691 bytes
raw SHA-256                            798c545acc5351eb9ed84f353c1fcc665a26967426e3761b7097e7f3c7042424
structured records                    237 across NSE segments
CM 2026 closure rows                  20
focused calendar tests                7 passed
full backend                          143 passed in 46.02s
frontend acceptance                   92/92 passed
runtime 2026-07-11                    CLOSED_WEEKEND
missing annual coverage               WAIT_CALENDAR_DATA
```

Scheduled scans stop before source work when the calendar is missing or closed. Manual historical/offline research remains available and records `EXCHANGE_CALENDAR` as a non-execution gate.

## Official Market Context Bootstrap

The live 2025-08-15 through 2026-07-10 bootstrap used direct NSE archive artifacts only.

```text
calendar weekdays attempted           236
index artifacts structured            220 unique sessions plus current re-fetch
expected holiday/no-file responses    16
transport/schema failures             0
elapsed                               63.21 seconds
Nifty 50 observations                 220
India VIX observations                220
latest EQ breadth rows                2,370
latest common source date             2026-07-10
market result                         RANGE / SOFT_FAIL
sector contexts                       10
```

Verified current hashes:

- all-indices close: `8371436f58823e11c2bb24884214963d98fa3d67d4a4ff30928c7be60f6a193c`;
- CM UDiFF bhavcopy: `660cf29855d55df43cb205615d544eda6c9a068de0fb2566cdebd9a8612cb87d`.

The 63.21-second result measures a first-time network/archive bootstrap; network time is deliberately excluded from the cached scanner SLA.

## Final Cached Scanner And Quality Audit

The benchmark uses exactly 50 official-current Nifty 50 constituents and runs
the complete cached scanner path on deterministic, locally stored candles. It
does not use the network and cannot create executable output.

```text
symbols                              50
cached candles                       11,000
processed series                     50
candidates                           50
scanner status                       COMPLETE
scan time                            10.2058 seconds
target                               less than 30 seconds
result                               PASS
data trust                           SYNTHETIC_TEST_CACHED_OFFLINE
executable                           false
```

Final automated verification after source-health hardening:

```text
backend tests                        162 passed in 35.61s
frontend acceptance                  95/95 passed
Ruff lint                            all checks passed
Ruff format                          85 files formatted
mypy                                 no issues in 67 source files
compileall                           passed
source URL governance                211/211 classified
active source contracts              30/30
```

`pip install --dry-run -r backend/requirements-dev.txt` succeeds. A global
`pip check` is not a valid isolated TrendForge dependency result because the
machine also contains unrelated packages with conflicts involving
`alpaca-trade-api`, `browser-use`, `playwright` and `pyppeteer`. TrendForge's
requirements do not introduce those packages; deployment should use the
documented virtual environment.

Security boundary: the server binds to localhost, CORS defaults to localhost,
secrets are environment-only, request models reject broker-order fields, and
no place/modify/cancel order endpoint exists. Expanding network exposure or
connecting OpenAlgo requires authentication, secret storage and a separate
execution authorization review.

Final live verification on `http://127.0.0.1:8001/` loaded 30 operational
source-health rows. NSE cash bhavcopy and all-indices close both display GREEN
with data date `2026-07-10`; a later calendar skip does not erase that latest
successful structured artifact. The radar contains only persisted guarded
research candidates and no `WAIT_DEMO_DATA` candidate. Desktop and 390px
mobile checks report no horizontal overflow and no console warning/error.

## Artifact Integrity And NSE F&O UDiFF Verification

Every structured parser now receives a common artifact-integrity result before
normalization. The gate records downloaded SHA-256 and byte length, validates an
HTTP `Content-Length` when supplied, optionally verifies a real external
manifest hash, rejects HTML returned for a data URL, and validates ZIP member
paths, encryption, count, uncompressed size, compression ratio, CRC and
per-member SHA-256. Bad artifacts remain archived for audit but cannot create
structured rows.

The live official NSE F&O UDiFF archive was then verified without cookies or a
landing-page scrape:

```text
URL          https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20260710_F_0000.csv.zip
HTTP         200
bytes        1,151,276
SHA-256      2933ae94177caa455aefaea1c95caf3c1b2e95c2ad8cd8de1746919605e870a2
member       BhavCopy_NSE_FO_0_0_0_20260710_F_0000.csv
data date    2026-07-10
rows         36,565
snapshot     309
parse        320
integrity    PASS
```

UDiFF supplies official EOD contract/OI/volume/basis context. It does not
supply synchronized live option prices or independently unlock G13; fresh
symbol-level MWPL and the remaining derivative dependencies are still required.

The first post-integration full-suite run exposed a flaky cached-scan SLA: the
same benchmark varied between 29 and 34 seconds. Profiling showed 957 redundant
`init_db()` calls consuming roughly 22 seconds. Initialization is now
process-idempotent per resolved database path. The complete benchmark fell to
10.2058 seconds, and the full 162-test suite fell to 35.61 seconds while still
creating isolated temporary databases correctly.

Guide items deliberately not copied: a universal 1 KB minimum, opening ZIP
bytes as text, assuming NSE publishes an expected hash manifest, the guessed
cookie-dependent historical API, approximate URL-group counts, and the proposed
rollover sum formula. These either reject valid official files, mis-handle
containers, were not live-verified, or are not sufficiently defined for
point-in-time trading evidence.

## 2026-07-11 Source Integration Analysis Slice

```text
Input audit: 1,552/1,552 lines, 10,957 words
Input SHA-256: 878b43c1d3485dce98bd4096103c010ac89090b502cb41ffd09722268a0648ae
Backend: 174 passed in 37.83s
Ruff lint: PASS
Ruff format: 88 files formatted
Mypy: no issues in 68 source files with repository ignore-missing-imports policy
Compileall: PASS
Frontend: 95/95 PASS
Runtime: health ok, guarded-research, 127.0.0.1:8001
Browser: RANGE loaded, zero console errors/warnings, zero horizontal overflow at 1248px
```

Live source assertions:

- NSE F&O ban parsed only `KAYNES` from the official 2026-07-13 file; G13 returned `BLOCKED_FNO_BAN` for that symbol.
- Ban-only evidence remained coverage-limited and did not satisfy MWPL percentages.
- NSE bulk deals persisted 89 fresh structured rows from the 2026-07-10 official file.
- CFTC persisted 10 relevant position rows from the 2026-07-07 report with publication-aware freshness.
- Missing UDiFF OI/OI-change columns returned `WAIT_SCHEMA_MISMATCH`.
- Guessed MWPL and MCX download patterns were absent from direct resolver candidates.
- OpenAlgo history and option-chain tests verified the documented POST paths, request contracts, localhost restriction and no order surface.

## 2026-07-12 Cross-Project Integration Validation

```text
TrendForge full backend suite                    181 passed in 32.38s
OpenAlgo client/adapter/export focused suite     10 passed
Trade Vision TrendForge intake focused suite      6 passed
Trade Vision OpenAlgo adapter focused suite       6 passed
Trade Vision full API suite                       exceeded 240-second runner window; no completed result claimed
```

Live loopback proof used separate ephemeral HMAC secrets and persisted no
credential values. TrendForge produced a signed evidence packet; Trade Vision
verified schema, content hash, signature, producer identity, timestamp and the
no-execution envelope before storage. The observed packet was
`ACCEPTED_RESEARCH_ONLY`, with two candidates and zero review-eligible
candidates. No `/api/v1/placeorder` request was issued.

Contract audit found and fixed one integration defect: OpenAlgo accepts daily
history as `D`, not yfinance-style `1d`. Regression tests require translation
of TrendForge `1d` and weekly-source requests to OpenAlgo `D` while preserving
TrendForge candle timeframe labels.

Incomplete-run regression proof:

```text
failed run id/status/finished             14 / ERROR / true
last completed export run                 12
Trade Vision intake                       ACCEPTED_RESEARCH_ONLY
intake candidates                         2
review candidates                         0
OpenAlgo handoff                          false
```

An older RUNNING record created during the failure test was explicitly closed
as ERROR after the corrected boundary was verified.

## 2026-07-13 Source Inventory And Normalization Validation

```text
211-row dry audit                    PASS
manifest hash                       d9ca34f23fef2b22310957fe2448faee37308799207ce83913a863b5a84f969d
bounded network maximum             25 IDs per run
clean pilot                         2 CSV plus 4 JSON candidates
raw archive                         SHA-256 content addressed
audit READY authority               always false
FRED real yield                     5,883 rows, FRESH at 2026-07-09
FRED broad dollar                   5,139 rows, STALE at 2026-07-02
backend full suite                  201 passed in 42.92s
frontend acceptance                 95/95 passed
Ruff lint/format                    passed, 97 files formatted
Mypy                                no issues in 72 source files
Compileall                          passed
```

The first parallel verification run caused only the cached Nifty 50 SLA test to
exceed its timing threshold under concurrent pytest/mypy/frontend load. The
isolated benchmark passed both tests in 14.39 seconds, and the subsequent full
backend suite passed sequentially. No correctness failure was hidden.

HTML and metadata behavior was tested fail-closed: presentation pages may yield
link/table/embedded-JSON profiles, but they remain metadata until a source-keyed
schema parser validates dates, fields, scope and freshness. JSON envelopes such
as BSE's `table` list are profiled by their nested records rather than reported
as a one-row object. FRED missing observations are skipped and counted, never
coerced to zero.

## 2026-07-13 Pending-Link Activation Validation

```text
pending manifest rows                      146
network-audited rows                       146
new structured official contracts           3
EIA parsed rows                             19
MCX FUTCOM parsed rows                     143
MCX option rows safely excluded         15,934
NSE SLB aggregated symbols                 235
SLB invented volume                          0
```

Live hashes: EIA `146cf38443b51a2d298b29ee95319012e8ef7ddec788085ff7394f45c0e9f6f3`,
SLB `a2201b4c06d1e8f30a4115f62e437bf8bc1da4356cee949e2c3016ac53058844`,
CFTC `7733ce1d4ba953e96206f3e1393150734f871a231b9350262910de5b66252806`,
and F&O `2933ae94177caa455aefaea1c95caf3c1b2e95c2ad8cd8de1746919605e870a2`.

Failure tests cover malformed MCX embedded JSON, option exclusion, SLB
aggregation, absence of invented SLB volume, same-organization artifact
following, private/unrelated artifact rejection and global-footer filtering.

```text
backend tests              212 passed in 39.53s
Ruff lint/format           passed, 101 files formatted
Mypy                       no issues in 73 source files
Compileall                 passed
Frontend acceptance        95/95 passed
Runtime health             ok on 127.0.0.1:8001
Fresh structured contracts MCX, SLB, EIA, CFTC and NSE F&O
```

## 2026-07-13 AMFI Scheme-Wise Validation

```text
official directory funds                 56
latest populated quarter        Jan-Mar 2026
normalized data date             2026-03-31
successful fund responses                 2
official Nil/no-data responses            54
unresolved fund failures                   0
parsed source rows                        460
persisted source rows                     460
monthly quantity deltas created             0
backend full suite                 218 passed
frontend acceptance                  95/95
Ruff lint/format                       passed
mypy                              74 files, passed
compileall                              passed
```

Failure coverage includes empty newest-quarter fallback, invalid directory,
schema mismatch, partial fund coverage, official `Nil`, absence of quantity,
quarter-end freshness and prevention of quarterly rows entering monthly
quantity-delta storage.

## 2026-07-13 FII/DII And NAV Validation

```text
NSE FII/DII live rows                    2
NSE FII/DII data date          2026-07-13
AMFI NAV live rows                  14,216
AMFI NAV latest date             2026-07-12
BSE proposed ZIP                  HTML FAIL
NSE option-chain payload                 {}
PIT current records                       0
fresh structured contracts               17
structured stale contracts                1
partial/metadata contracts                7
unconnected contracts                     9
backend tests                     223 passed
frontend acceptance                  95/95
Ruff, format, mypy, compileall        passed
```

Tests verify exact AMFI headers, scheme context, malformed rows, NAV scope,
FII/DII category normalization, buy-minus-sell reconciliation, duplicate
categories and official direct-download candidates.

## 2026-07-13 Supplemental Endpoint Validation

```text
registered source contracts                 38
fresh structured contracts                  18
structured stale contracts                   1
partial/empty/wrong-content/metadata         10
unconnected contracts                        9
live block-deal context rows                  1
option-chain current state          NO_DATA_NOW
PIT current state                   NO_DATA_NOW
BSE bhavcopy current state    WRONG_CONTENT_NOW
backend tests                         229 passed
frontend acceptance                       95/95
```

Parser tests cover empty and populated option chains, empty PIT, BSE HTML,
valid BSE ZIP parsing and block-deal scope restrictions.

## 2026-07-13 Surveillance And FPI Source Validation

```text
live ASM rows                              185
live GSM rows                                0 valid empty
live pledge source rows                  1,532 persisted 1:1
live OI-spurt rows                          215
live NSDL normalized rows                    34
NSDL cash/debt rows                          25
NSDL derivatives rows                         9
registered source contracts                  43
fresh structured contracts                   24
backend tests                         239 passed
frontend acceptance                       95/95
Ruff lint                                  passed
Ruff format                  110 backend files clean
mypy                         78 files, passed with external untyped imports ignored
compileall                                  passed
```

Regression coverage verifies valid-empty GSM normalization, G03 clean-symbol
pass, ASM/GSM symbol veto, exact pledge row preservation, pending symbol
mapping, OI-spurt scope without MWPL inference, NSDL cash/debt normalization,
NSDL derivatives normalization, raw archive lineage and frontend drilldown
availability. A batch-scanner regression also proves that an ASM-listed symbol
is persisted as `REJECT` with a symbol-level `G03_STOCK_SAFETY` veto.

The attached code's printed success statements were not accepted as proof.
Every live source was fetched through TrendForge, hash archived, parsed,
source-dated, normalized and queried back from SQLite.

## 2026-07-13 Gold And Physical-Market Source Validation

```text
WGC open-interest rows                1,256 fresh structured
WGC ETF holdings rows                 5,839 fresh structured
WGC ETF flow rows                     2,225 fresh structured
SGE daily report rows                    17 fresh structured
LME warehouse contract      monitored/access blocked
MCX delivery contract       monitored/access blocked
registered contracts                         48
MCX_CONTEXT                    WAIT_SOURCE_SNAPSHOT
current blocker                            USD/INR
focused parser/contract tests                   16 passed
backend full suite                            248 passed
frontend acceptance                             95/95
Ruff lint/format, mypy, compileall              passed
```

Regression tests cover schema failure, wrong endpoint selection, gold-price
separation from ETF tonnes, derived-total behavior, SGE numeric normalization,
date-bounded resolution, normalized-row lineage, full-snapshot stale-row
removal, blocked-source visibility and preservation of the MCX core pass set.

Post-restart HTTP verification passed for `/api/health`, source catalog,
freshness, parser domain rows and gate readiness on PID 27516.

## 2026-07-13 Institutional Engine Validation

Commands:

```text
cd D:\TrendForge\backend
python -m pytest -q
python -m ruff check trendforge_api tests tools
python -m ruff format --check trendforge_api tests tools
python -m mypy trendforge_api --ignore-missing-imports
python -m compileall -q trendforge_api tests tools
python -m tools.audit_institutional_endpoints --output ..\data\reports\institutional_endpoint_audit_latest.json --concurrency 4
cd ..\frontend
npm test
node --check app.js
```

Results: 265 backend tests, 104/104 frontend checks, Ruff, mypy and compileall
passed. The 37-contract network audit returned 20 raw payloads, six valid
current empty payloads, nine HTTP failures and two non-JSON BSE payloads.

Failure coverage proves: stale fallback cannot score; wrong content is archived
before parse failure; raw JSON cannot score; missing factors, surveillance,
untrained models and anomaly detection block sizing; API clients cannot
self-certify readiness; walk-forward training ends before every evaluated row.

Remaining validation gap: no directional model has a persisted, calibrated
artifact and the 20 raw-only contracts are not all normalized. Production
classification and OpenAlgo execution therefore remain blocked.

Runtime verification on PID 24868 passed at `http://127.0.0.1:8001/` in
`guarded-research` mode. Desktop and 390x844 mobile browser checks showed the
Institutional Factor Engine without overlap or horizontal overflow, and the
browser console reported no errors. The running API also rejected a request
that attempted to self-certify source and model readiness, returning
`WAIT_SOURCE_STRUCTURED_PENDING` with quantity zero.

Container validation is pending because Docker is not installed in this
workstation environment. The Dockerfile is present but has not been build-run.

## Source Documentation Merge Validation - 2026-07-14

```text
merged source artifacts                   21
embedded original content bytes   27,833,447
TF_SOURCE_BEGIN markers                   21
TF_SOURCE_END markers                     21
verbatim segment SHA-256 mismatches         0
moved source artifacts                    20
active superseded artifacts                0
211-row inventory views                    4
unique inventory IDs per view            211
unique URLs per view                      211
pending audit rows per view               146
```

Master file SHA-256 after consolidation:
`7ff1394b34a4484b0166832d3fde88553a727e1a96e99d6512d8355a997fb50d`.

This was a documentation-only consolidation. Backend and frontend behavior
were not changed, so the existing application test results remain applicable.

## 2026-07-15 Priority Adapter Validation

```text
backend focused commodity/BSE/AMFI tests    19 passed
backend full pytest                         300 passed
backend compileall                              passed
frontend JavaScript syntax                      passed
frontend acceptance checks                 119/119
```

Failure coverage includes zero option OI, no invented SGE/LBMA premium,
writer-payout max pain, stale fallback visibility, BSE HTML rejection, current
UDiFF ZIP/direct CSV schemas, and AMFI added/reduced/exited position deltas.

Live/bounded artifact checks produced NSE UDiFF 2,382 rows and BSE UDiFF 4,857
rows for 2026-07-15. The fresh MCX seed returned 403 and Baker Hughes refresh
timed out, so both retained validated stale artifacts and did not become fresh.

Post-start runtime verification passed at `http://127.0.0.1:8001/`:
`/api/health` returned `ok`; the commodity endpoint returned three source states,
one MCX metric set, SGE and Baker Hughes context, and `canUnlockReady=false`.
Browser verification showed all three context rows, no console errors, no
horizontal document overflow, and no internal list overflow at the active
desktop viewport.


---

## 2026-07-16 Scanner Parser Link Update

Fresh structured usable inventory links increased from 45 to 47 after the 13-source scanner parser verification. BSE block-deal rows now have fresh structured evidence. Live verification summary: 13 sources fetched, 8 raw archived fresh, 4 valid empty, 1 stale fallback, 0 broken, 3176 normalized disclosure events. Canonical current files are `D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-16.csv` and `D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-16.xlsx`.

## 2026-07-28 FMR-011 Plan Registration Validation

```text
coverage rows                              155
FMR-011 coverage rows                        1
FMR-011 mapping                    R15/R16/R18
coverage-generator Python syntax          PASS
runtime Paper Lab                   NOT BUILT
objective outcome worker            NOT BUILT
offline challenger retraining       NOT BUILT
broker/order/quantity permission        NONE
```

Validation was limited to plan consistency, generator syntax, coverage
regeneration and duplicate-ID checks. Existing journal and ML snapshot routes
were observed in code but were not reclassified as the completed learning loop.
No backend or frontend regression suite was run because runtime code did not
change.

## 2026-07-30 Professional Mathematics Reconciliation Validation

`	ext
validator/test Python syntax                         PASS
governance validator focused pytest            26 passed
coverage rows                                          155
coverage added / removed / changed                  0/0/0
D-ID inventory                                     30 IDs
latest lasting decision                              D-030
protected runtime manifest before  643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D
protected runtime manifest after   643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D
runtime source changes                                  NONE
`

The structural checks require the mathematics authority boundary, general and
conservative EV, finite-horizon barrier definition, alpha-adjusted factor
residual, all four observable OI codes, File A FUS-009, cash-Gamma and
corporate-action crosswalk entries, File A section 25.22, Hybrid/Final
Merge/Discovery/Architecture mappings and decision D-030. Trap tests remove
the finite-horizon definition and reintroduce LONG_BUILD_UP as an observed
state; both fail closed.

The changed-file validator covered every edited documentation/governance path
and required the unchanged runtime-manifest baseline. The coverage CSV did not
change because this reconciliation maps existing R/FTR/DAT/FUS owners rather
than creating a new implementation requirement. Backend/frontend regression
suites were not rerun because no runtime file changed; containment was verified
by the manifest. This evidence does not claim implementation of probability,
EV, order-book microstructure, source activation or production readiness.
## 2026-07-30 - Professional mathematics VRP reconciliation validation

**Scope:** Documentation-only synchronization of dividend-aware Theta, local delta-hedged variance attribution and variance-risk-premium research context across File A, Final Merge, Hybrid, Discovery, Options, Architecture, D-030, file navigation and remaining-build governance.

Primary research evidence checked:

- Federal Reserve, *Expected Stock Returns and Variance Risk Premia*: variance risk premium is based on implied versus realized/expected variance and the cited results depend materially on model-free implied variance and high-frequency realized variance.
- Federal Reserve, *The Variance Risk Premium Around the World*: formal distinction between risk-neutral and physical expected return variation; model-free implied variance is preferred over a Black-Scholes ATM proxy.

Focused command:

```powershell
python -m py_compile docs\fable\remaining_build\build_coverage_csv.py docs\fable\remaining_build\test_build_coverage_csv.py
python -m pytest docs\fable\remaining_build\test_build_coverage_csv.py -q
```

Observed:

```text
26 passed in 0.55s
```

Containment and coverage command:

```powershell
python docs\fable\remaining_build\build_coverage_csv.py --check --print-runtime-manifest-hash --expected-runtime-manifest-hash 643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D --changed-file <each reconciled documentation/governance file>
```

Observed:

```text
643D69BAB19A03302B1AFD1619803E45834C51CCDFF0138C5EB689434C12C64D
Rows: 155; added=[]; removed=[]; changed=[]
P0 build rows=41; P0 not implemented=48
```

Adversarial behavior verified:

- removing the canonical VRP mathematics section fails validation;
- removing Options `VRP_UNKNOWN` handling fails validation;
- adding `Positive VRP means sell options` fails as an unsafe automatic trade command;
- existing finite-horizon, observable-OI, decision-ID, FMR-owner, detail-tag and runtime-containment traps remain passing.

Caveat: this validation proves document consistency and containment only. It does not prove live option-chain completeness, model-free implied variance, a PIT realized-variance forecast, trading costs, calibration, predictive edge or production feature readiness.

## 2026-07-30 - Options and VRP usefulness verdict

**Verified:** The `R0 -> R12 -> R16 -> R18` sequence improves evidence
reliability by requiring compatible source contracts, synchronized option
timelines, point-in-time calibration and model governance before any promoted
VRP interpretation. It also keeps incomplete evidence at `VRP_UNKNOWN` and
prevents the options package from independently authorizing direction or
`CONFIRMED`.

**Not yet verified:** live ingestion, scanner-ready calculations, replay
correctness, realized trading costs, out-of-sample predictive improvement,
win-rate improvement, production API/storage integration and rendered
frontend behavior.

**Acceptance boundary:** the idea is validated as an architecture and
false-confidence control. Trading usefulness remains a hypothesis until R12,
R16 and R18 pass their runtime, point-in-time and governance acceptance tests.

## 2026-07-30 - Conditional VRP research-proposal amendment validation

Documentation scope now permits a future non-executable
`VRP_RESEARCH_PROPOSAL` only after File A section 25.23 gates pass. Required
negative behavior is:

- incomplete or incompatible evidence -> `NO_RESEARCH_PROPOSAL`;
- missing stressed-loss, liquidity, concentration, scenario-margin or hedge
  input -> null research quantity;
- naked or unbounded-loss short-volatility structure -> rejected;
- proposal cannot alter public state or evidence votes;
- no broker/account/order/execution path.

This documentation amendment is not runtime implementation or observed trading
validation.

## 2026-07-30 - Source-result freshness and valid-empty hardening validation

Scope:

- `backend/trendforge_api/source_contracts.py`
- `backend/trendforge_api/selection/fixtures.py`
- `backend/tests/test_q5_selection_contracts.py`

Focused command:

```powershell
cd D:\TrendForge\backend
python -m pytest tests\test_q5_selection_contracts.py tests\test_source_contract_hardening.py tests\test_source_runtime_hardening.py -q
```

Observed: `26 passed in 2.82s`.

Complete backend command:

```powershell
python -m pytest -q
```

Observed: `537 passed in 114.25s`.

Compilation and frontend checks:

```powershell
python -m py_compile trendforge_api\source_contracts.py trendforge_api\selection\fixtures.py tests\test_q5_selection_contracts.py
cd D:\TrendForge\frontend
cmd /c npm test
```

Observed: compilation passed; frontend contract checks and acceptance checks
passed **135/135**.

Adversarial behavior observed:

- fresh valid-empty evidence remains `VALID_EMPTY` but is not confirmation
  eligible and has ceiling `WAIT`;
- structured evidence without explicit freshness proof remains
  `STRUCTURED_OK/UNKNOWN` and cannot confirm;
- explicit fresh structured evidence under an approved role can be
  confirmation-eligible;
- explicit stale evidence returns `STALE`, `STALE_SOURCE`, and `WAIT`;
- direct construction of confirmation-capable `VALID_EMPTY` evidence fails
  model validation.

Caveat: these tests verify deterministic contract behavior. They do not verify
live endpoint access, calendar-specific freshness production wiring, source
activation, predictive usefulness or production readiness.

## 2026-07-30 - Live populated source-data validation

Validation criterion: a link counts as producing usable data only when the
implemented parser returns meaningful normalized records for scanner use.
HTTP `200`, a parser invocation, metadata, or a valid-empty response does not
count as populated trading data.

Observed across all 39 parser-backed catalog entries:

```text
catalog entries                                      74
parser-backed links tested live                      39
populated normalized data                            29
structured valid-empty                                2
unproven empty parses                                 3
metadata-only                                         3
schema mismatch                                       2
catalog links without structured parser              35
```

Representative populated observations:

```text
nse_fo_bhavcopy                                  31,284 rows
nse_equity_universe                              2,390 rows
nse_oi_spurts                                      213 rows
nse_large_deals                                    106 rows
nse_asm                                            191 rows
nse_gsm                                             82 rows
```

All 39 tested routes returned HTTP `200`, demonstrating why transport status
alone is not evidence of usable data. The correct current answer to "how many
links return actual stock, option or other scanner data?" is **29 of 74 catalog
links**. The two valid-empty links are tracked separately and cannot vote,
produce a candidate, or support `CONFIRMED`.

Remaining non-populated parser-backed issues:

- `amfi_monthly_portfolio`, `nse_option_chain` and `nse_pit_current`:
  unproven empty parse;
- `bse_buyback_tender`, `bse_takeover_open_offer` and `sebi_pit_sast`:
  metadata-only;
- `amfi_scheme_wise` and `nse_mwpl_percentages`: schema mismatch;
- `nse_daily_buyback` and `nse_fno_ban`: structured valid-empty.

Source activation remains disabled. This validation proves live populated
records and parser classification, not gate authorization, predictive edge or
production readiness.

## 2026-07-30 - AMFI/BSE source correction validation

Success criterion: only schema-valid parsed rows count as data. HTTP `200`, a
download suffix, metadata, or parser invocation alone does not count.

Observed live through the existing monitor/parser/storage pipeline:

```text
amfi_scheme_wise monitor          CHANGED, HTTP 200, 139,494 bytes
amfi_scheme_wise parse            PARSED_STRUCTURED
amfi_scheme_wise data date        2026-06-30
amfi_scheme_wise rows             440
AMFI fund coverage                56 requested / 2 populated / 54 valid-empty
AMFI failed funds                 0
amfi_nav parse                    PARSED_STRUCTURED, 14,217 rows, 2026-07-30
bse_bhavcopy_eod parse            PARSED_STRUCTURED, 4,872 rows, 2026-07-30
amfi_monthly_portfolio            WAIT_EMPTY_PARSE, 0 holdings rows
```

Persisted domain evidence after the run:

```text
amfi_nav_observations             22,832 rows
amfi_scheme_exposure_rows          1,360 rows; max quarter 2026-04-01
amfi_scheme_holdings                   0 rows
amfi_stock_deltas                      0 rows
bse_cash_eod                       9,729 rows; max data date 2026-07-30
```

Regression commands and observations:

```powershell
cd D:\TrendForge\backend
python -m pytest tests\test_amfi_scheme_wise.py tests\test_supplemental_market_sources.py -q
# 17 passed

python -m pytest -q
# 540 passed

cd D:\TrendForge\frontend
cmd /c npm test
# 135/135 passed
```

Adversarial proof covers HTTP `200` `Nil`/`No data found.` as explicit
valid-empty and HTML disguised behind `.csv`/`.zip` as non-data. AMFI data
remains delayed context; NAV cannot prove stock holdings; quarterly exposure
cannot prove quantity change or intraday flow. No activation or predictive-edge
claim was made.

## 2026-07-30 - Eight-source and BSE XBRL validation

The attached prototype logs were not accepted as proof. The same source
families were fetched through TrendForge's persisted native contracts.

```text
fred_broad_dollar_index          PARSED_STRUCTURED   5,154   2026-07-24
fred_real_yield_10y              PARSED_STRUCTURED   5,896   2026-07-28
mcx_bhavcopy                     PARSED_STRUCTURED     144   2026-07-29
nsdl_fpi_daily                   PARSED_STRUCTURED      34   2026-07-30
cftc_cot                         PARSED_STRUCTURED      11   2026-07-21
eia_weekly_petroleum_stocks      PARSED_STRUCTURED      19   2026-07-24
bse_buyback_tender index         PARSED_METADATA_ONLY   76   2026-07-24
bse_takeover_open_offer index    PARSED_METADATA_ONLY  158   2026-07-28
```

BSE detail observation:

```text
buyback linked XBRL documents archived/parsed       140 / 140
takeover linked XBRL documents archived/parsed      267 / 267
detail-fetch failures                                         0
current positive-term buyback rows                            67
current positive-term takeover rows                          140
buyback rows resolved to NSE symbols                          67
takeover rows resolved to NSE symbols                         31
up-to-date rerun state                             STRUCTURED_OK
```

Runtime examples observed after point-in-time ISIN mapping included `NIRAJ`
at INR 29 for 15,520,529 shares, `RBA` at INR 70.39 for 208,061,717 shares,
`IIFLCAPS` at INR 350 for 100,144,112 shares, `SAMMAANCAP` at INR 139 for
341,754,286 shares and `KWIL` at INR 21.33 for 610,893,729 shares. A legacy
zero-price/zero-quantity row produced no evidence claim.

```powershell
cd D:\TrendForge\backend
python -m pytest tests\test_bse_offer_xbrl.py -q
# 8 passed

python -m pytest -q
# 541 passed

cd D:\TrendForge\frontend
cmd /c npm test
# 135/135 passed
```

The index payloads remain metadata/discovery by design; only validated linked
XBRL terms enter `corporate_offer_events`. Delayed CFTC/FRED/EIA/NSDL context,
MCX EOD rows and BSE offer anchors retain their declared scope and cannot
independently create `CONFIRMED`.

## 2026-07-30 - Old-versus-pasted download validation

Validation used populated, schema-valid records rather than HTTP transport
status. The retained comparison is:

```text
source purpose                  old usable    pasted usable    selected use
nse_bhavcopy_eod                     2,409            3,132    hybrid
nse_preopen_scope                      208               50    canonical FO (broader scope)
nse_all_indices                        139              139    equivalent
nse_asm                                191                0    canonical
bse_buyback_tender                      67               69    canonical + archive
bse_takeover_open_offer                140              148    canonical + archive
cftc_cot                                11            7,847    hybrid
eia_weekly_petroleum_stocks             19               19    hybrid
fred_broad_dollar_index              5,154            5,154    canonical
fred_real_yield_10y                  5,896            5,896    canonical
mcx_bhavcopy                           144           16,435    pasted research archive
nsdl_fpi_daily                          34                0    canonical
```

MCX validation required populated symbol, instrument, close, volume and OI
fields. All 16,435 contract rows met that schema; 1,112 had positive volume or
OI and are the narrower liquidity-active subset. BSE usable detail counts
required positive offer price plus positive quantity/offer size. CFTC counts
are intentionally different scopes: 11 latest normalized canonical rows versus
7,847 retained historical prototype rows.

Archive observation:

```text
root             data/raw_sources/verified_downloads/2026-07-30
retained files   444
retained bytes   15,606,922
comparison       OLD_VS_NEW_USABLE_DATA_COMPARISON.csv/.json
```

This validates downloaded research artifacts and identifies the preferred
implementation per source. It does not prove predictive value, source
activation, live intraday freshness or confirmation authority.

## 2026-08-01 - Single-spine residual governance re-verification

```powershell
python -m pytest docs/fable/remaining_build/test_build_coverage_csv.py -q
# 26 passed

python docs/fable/remaining_build/build_coverage_csv.py --check
# Rows: 155; added=[]; removed=[]; changed=[]

python docs/fable/remaining_build/build_coverage_csv.py --print-runtime-manifest-hash
# 07E2F9E7C107CF480D1A98CE4AF9B30547B1BA23580DF7123C971A98360D85BB
```

The Discovery and Options detail plans contain none of the forbidden
pick-next-M, competing-order or hard-coded activation instructions. D-025,
D-028 and D-029 are present and top-level D-IDs are unique. File A section
25.21 and Q4W-006 both preserve the `FMR-011` R15/R16/R18 ownership split.
The remaining-build work packet selects only File A `R0-R18`, `CROSS-###` or
`TDG-GAP-###` requirements and never M/T/PK detail tags. No runtime product,
live frontend, activation, database, broker or scanner business logic changed.
## 2026-08-01 - Plan crosswalk and score-law lock validation

Scope: governing docs only.

Verified by edit review against File A section 9 and FMR-002:

1. Build stage IDs remain File A SEL-001..010; FMR-002 S0-S9 marked story-only with explicit map.
2. Public state owner and forbidden Combined_Score language recorded.
3. Discovery modes A-E and integrity G1-G8 locked to Discovery meanings; not generic TA / not File A G00-G14.
4. R0 residual checklist listed under remaining_build Step B.

Governance suite should still pass (docs-only; no FMR owner-map ID change):

`powershell
python -m pytest docs/fable/remaining_build/test_build_coverage_csv.py -q
python docs/fable/remaining_build/build_coverage_csv.py --check
`

Verdict: **DOCUMENTED**. Not a claim of R0 product completion or source activation.
Observed after fileindex restore: governance tests 26 passed; coverage 155 rows zero drift.

## 2026-08-02 - Options Best Research Playbook validation

Scope: docs/OPTIONS_INTELLIGENCE_PLAN.md section 18 + fileindex pointer + section 4 package-narrative relabel.

Checks:
1. Public states remain WATCH|WAIT|CONFIRMED|REJECT only in playbook
2. OPTIONS_PACKAGE remains SUPPORT|WEAKEN|CONFLICT|UNKNOWN
3. Signed GEX scenario-only; max pain NOT A FORECAST GUARANTEE
4. Build work still R12 + File A S# crosswalk, not M-order
5. Governance suite should still pass (detail-plan wording only)

`powershell
python -m pytest docs/fable/remaining_build/test_build_coverage_csv.py -q
python docs/fable/remaining_build/build_coverage_csv.py --check
`

Verdict: DOCUMENTED playbook. Not R12 product implementation.

## 2026-08-02 - Options section 18 hybrid playbook validation

Scope: OPTIONS_INTELLIGENCE_PLAN.md section 18 only. Confirmed no new plan file.
Public states and package enums unchanged. Truth-behind-maths + self-test added.
Verdict: DOCUMENTED hybrid. Not live chain implementation.

## 2026-08-04 - Live panels M1-M3 validation

Observed frontend/static evidence:

```text
node tests/live_panels.test.js                         PASS
inventory-app Node suites (10 files)                 PASS
node --check live_panels.js / app.js                 PASS
Python AST parse (live_panels.py/main.py/tests)       PASS
browser with API unavailable                         OFFLINE fail-closed
Consensus                                             0 active / 0 symbols
Screener                                              no calculated rows
browser JavaScript errors                             0
```

Backend pytest was not runnable because the current Python installation lacks the repository dependencies. No install, live fetch, or real SQLite migration was authorized, so this is not a live-source activation claim. Detailed evidence: `docs/fable/LIVE_PANELS_IMPLEMENTATION_REVIEW_2026-08-04.md`.

Follow-up after explicit install approval:

```text
focused live-panel pytest                              10 passed
Ruff changed live files                               PASS
mypy live_panels.py                                   PASS
disabled HTTP route                                   200 / WAIT_DISABLED
real-network 10-source smoke                          10/10 populated
full legacy backend suite                             538 passed / 24 unrelated failures
```

Observed source rows after market close: `20, 20, 25, 20, 20, 139, 213, 213, 296, 208`. Intraday sources correctly failed the 300-second LIVE gate, prior-day large deals were quarantined, and all panels reported `MARKET_CLOSED`. The production database remains unchanged.

## 2026-08-06 - MD69 parameter-resolution validation

```text
focused registry/service/scheduler/parameter tests       55 passed
full live registry refresh                               COMPLETED
attempted / completed                                    69 / 69
BSE announcements                                        SUCCESS_NEW, 1 row
NSE shareholding                                         SUCCESS_NEW, 2,285 rows
NSE PIT                                                  VALID_EMPTY, 0 rows
NSE sector constituents                                  SUCCESS_NEW, 25 rows
NSE equity option chains                                 SUCCESS_NEW, 464 rows
```

Manifest:
`D:\TrendForge\data\market_data\2026-08-06\snapshots\manual-20260806-123411\manifest.json`.

Verdict: **VERIFIED WITH CAVEATS**. Failure isolation and the repaired
parameter flow are observed. Six unrelated sources still failed and one was
partial; no claim is made that all 69 feeds are populated.

## 2026-08-10 - Pack-2 context-source validation

Scope: `tradingeconomics_bdi`, `yahoo_bdry_shipping_proxy`, and
`google_trends_india_rss` only. No catalog, Consensus, Screener score, broker,
or background-scheduler activation was included.

Observed live through the existing TrendForge fetchers:

```text
tradingeconomics_bdi         HTTP 200  PARSED_STRUCTURED  2026-08-10    1 row
yahoo_bdry_shipping_proxy    HTTP 200  PARSED_STRUCTURED  2026-08-10  251 rows
google_trends_india_rss      HTTP 200  PARSED_STRUCTURED  2026-08-10   10 rows
```

Canonical stored object hashes:

```text
BDI     fc9075ef2c87418b6eedb78634222d1c30642d5463d049a4627f40f9d48b05a1
BDRY    c72c1ffe408a7a73dfeda449e9855dc1f5ce7bf487e499fa29a5ac2b7da0d684
Google  63a907bc6566f115091948ca580c5bcc37837b91b57eadbfca3b28f2ea210aed
```

Focused production re-run after the BDI parser v1.1 field correction:

```text
BDI     e5bb09bbc677f7e93a55389dda3014a85ce0278c5c5292e31ba39ccc8e80854b  attempt 1511
BDRY    e4cb7c4fc583faaa402e5a4ec092891c20dbc84523e3719a0b5534c91526022b  attempt 1508
Google  7a5b083fca58080268c8aa3cd5af462953e15e511134b0fce14d457f63fd325d  attempt 1510
```

The stored BDI row is dated 2026-08-10 and contains `value=3083`,
`previousValue=3089`, `dailyChange=-6`, and `dailyChangePct=-0.19`.

Guards observed by tests: invalid HTML/XML and empty rows fail closed; only
`BDRY` bars are accepted; BDRY can never be labelled official BDI; Google RSS
can never be represented as arbitrary keyword history; a failed refresh keeps
the last populated snapshot; the registry/compiler/scheduler discovers all
three dynamically.

```text
focused Pack-2 + registry + scheduler        43 passed
Pack-2 + registry + scheduler + dry-run      PASS
Python source compile                        10 files PASS
focused import + Ruff                         PASS
full backend                                 673 passed, 10 unrelated failed
```

The current stop-on-first-failure regression reached 144 passes before the
known unrelated `bse_pledge_data` timeout expectation failed (configured 120s
versus old test expectation 45s). No Pack-2 source key or changed file appears
in that failure.

Verdict: **VERIFIED WITH CAVEATS**. The three approved sources are fetched,
normalized, archived and stored through the production spine. Provisional
schedules remain disabled unless the existing explicit operator override is
used. No full 104-source manifest or frontend catalog projection is claimed.

## Pack-3 CRISIL and ICRA verification (2026-08-10)

- Focused offline suites: **45 passed** for rating parsers, resolver routing,
  registry pins, invalid/empty/future-date inputs, dedupe, unmapped companies,
  and CRISIL last-good retention.
- Registry: **106 rows / 106 unique keys**, with CSV/YAML/Python pins aligned
  and 106/106 executable acquisition/normalization coverage.
- CRISIL live: 39,491 reported total; bounded 100 archived and normalized;
  data date 2026-08-10; raw hash `7cb7fd29...`; attempt 1512.
- ICRA live: CSRF/session GET+POST; 20 normalized current rows; data date
  2026-08-10; raw hash `6e1456ec...`; attempt 1515.
- Catalog samples: CRISIL 100 and ICRA 20. Neither votes or changes formulas.

Verdict: **VERIFIED** for these two contracts. CARE and Google News RSS remain
viable but unimplemented; NewsAPI needs a key; StockEdge remains rejected.

### CARE source verification

CARE passed 37 focused parser/registry/regression tests. A live page-owned JSON
response archived 1,000/1,000 meaningful dated rows and the scheduler persisted
attempt 1516 as the current last-good object. Empty, wrong-schema, HTML shell,
invalid/future date, duplicate, unmapped and deterministic cases are covered.
`care_ratings` is verified as informational and zero-score.

### Google News RSS / Pack-3 closure

Google News RSS passed malformed JSON/XML, empty feed, invalid/future/stale date,
dedupe, determinism, resolver and registry tests. The combined focused suite is
**45 passed**. Live snapshot 492 archived SHA-256 `ab7c4a47...`; parser v1.0.0
examined 234 items and retained 4 fresh rows, and MarketDataService stored
attempt 1517 as `SUCCESS_NEW` (normalized object `ae205ae1...`). Registry CSV,
sidecar, YAML and Python pins agree at 108 unique keys. Catalog row 150 contains
the 4 records. The full Pack-3 ledger closes all ten candidates; NewsAPI is
BLOCKED by key/license approval and StockEdge plus the incomplete yfinance RRG
route are REJECTED. No scoring formula changed.

### USDA WASDE Pack-4 enhancement

The corrected official ESMIS endpoint returned release 795974 and the July
2026 XML. Live snapshot 493 is populated and parser v2.0.0 produced 5,414 rows
dated 2026-07-10 from `cell_value*` attributes; it rejected 6,137 filler cells.
Attempt 1518 is `SUCCESS_NEW` with normalized hash `fc81680f...`. Tests: 16
USDA/legacy repair tests passed, then 37 USDA/registry/Pack-3 regressions passed;
targeted parser/test Ruff passed. CSV/YAML/Python/sidecar pins agree at 108 keys
and SHA `B1EB1A7F...`. Catalog row 124 was force-refreshed safely and contains
250 sample rows from the 5,414-row last-good object. Verdict: **VERIFIED**.

### Angel One public master

Live snapshot 494 contained 152,044 meaningful public broker-master rows.
Parser tests cover identity, controls, invalid/empty/wrong-schema input,
dedupe, determinism and resolver wiring. The first full normalized form was
observed at 247 MB and failed the efficiency requirement; compact aggregation
was added and reverified. Current attempt 1520 stores 24,063 schedules in
28,713,705 bytes, with all 112,223 in-scope contracts represented and the full
source retained in the raw archive. Tests: 42 combined pass; 8 Angel focused
and Ruff pass. Registry/pins agree at 109 keys. Catalog row 151 has 250/24,063
sample/usable rows. Verdict: **VERIFIED WITH CAVEAT** â€” attempt 1519's orphaned
object awaits normal retention cleanup and is not the last-good pointer.

### Dhan public detailed master

Snapshot 495 archived 205,781 rows and parser v1.0.0 accepted 155,175 current
product-scope rows into 24,283 compact schedules. An adversarial live check
found 10,104 false duplicates under exchange + security ID; adding segment to
the identity reduced true duplicates to zero. Attempt 1522 supersedes attempt
1521 and is `SUCCESS_NEW`, 35,119,182 bytes, hash `f6734776...`. Tests: 33
combined pass; 7 focused plus Ruff pass. Registry pins agree at 110 keys;
catalog row 152 contains 250/24,283 sample/usable rows. Verdict: **VERIFIED**.

### Dead source route quarantine

- `backend/tests/test_dead_source_route_quarantine.py`: **4 passed**.
- `backend/tests/test_market_data_registry.py`: **13 passed**.
- saved-link machine-readable classification check: **1 passed**.
- changed Python files: compile succeeded with isolated bytecode output.
- observed counts unchanged: registry **119/119**, catalog **161 rows / 125
  active logical keys**.
- dead BSE prototype stubs contain no request/write calls and are absent from
  its main routine; every approved replacement exists in registry, profiles and
  frontend catalog.

Verdict: **VERIFIED** for the approved quarantine milestone. No live fetch was
needed because this is a fail-closed routing and regression change.

### FII stock-name signals API and display

- focused backend: `tests/test_fii_stock_signals.py` â€” **5 passed**;
- saved database API smoke â€” **HTTP 200**, **106** large deals, **33** symbols,
  **0** quarterly FII/FPI changes;
- inventory Node suite â€” **all tests passed**, including placement, escaping,
  fail-closed response handling and consensus hash isolation;
- browser observation â€” panel visible below Nifty Filter and above Screener,
  20 compact large-deal pills shown (+13 more), zero console errors;
- protected `consensus.js` SHA-256 remains
  `1FA7BB2369D1C840D5DDD8B491BFECEEA15B65A843FC9B2BCCA48BB824672330`.

Full backend regression result: **794 passed, 20 failed**. The 20 failures are
pre-existing/unrelated contract, IV-rank, Upstox, workbook-hash, NSE mock and
Vyom expectations; none references the new module, route or focused test.
Therefore the milestone verdict is **VERIFIED WITH CAVEATS**, not a claim that
the entire pre-existing backend suite is green.


## Embedded Source Operations validation - 2026-08-15

```text
node --check frontend/product-fixture.js                 PASS
node --check ../trendforge_inventory_app/app.js          PASS
node --check frontend/inventory-workbench/app.js         PASS
source/bundled runtime asset hashes                       MATCH
Inventory drawer route and panel                         OBSERVED
stale filter detail rows                                  50 OBSERVED
```

The Inventory button loaded the same-origin route
`/inventory-workbench/?embed=terminal&v=20260815-source-operations`. The iframe
had the embedded class, the Source Operations panel appeared below the five KPI
cards, and the stale filter opened a list naming 50 sources. The panel kept
`VALID_EMPTY` separate from failure and showed activation and gate authorization
as separate non-authorizing values.

Observed run values were 354 compiler contracts, 132 monitored keys, 56
input-observed sources, 47 parsed-record sources, 5 current facts and 5
research-usable facts; status counts were 5 healthy, 1 valid-empty, 50
stale/partial, 0 blocked, 0 failed and 76 not-attempted. These values are for
that run only. The overlay is not a ranker, state engine, quantity calculator,
or execution path. Unrelated existing runtime warnings were refresh status 503,
selection/live 404 and favicon 404.


## Hash-pin caveat - 2026-08-15

The source and bundled runtime files contain aligned feature markers but are separate revisions and are not byte-identical for this
change, but the existing snapshot manifest still contains the pre-Source-
Operations byte sizes and hashes. The existing `inventory-workbench.test.js`
also still expects the old drawer URL without `embed=terminal`. Its current
observed result is **FAIL: Size mismatch: index.html**. This means the runtime
panel observation is valid, but the manifest/test pin must be refreshed before
claiming a clean snapshot-integrity verdict. No source data, catalog sample, or
TrendForge state authority is affected by this metadata/test discrepancy.

## Refresh/Scheduler post-commit bridge - 2026-08-15

Observed flow:

Refresh or Scheduler -> collector fetch and schema/parser validation -> raw archive, manifest and content-addressed last-good commit -> cash-relevant fingerprint check -> existing A1 -> A2 -> A3 -> A4 -> A5 -> A6 -> C0 -> conditional B -> C1 -> selection storage and Source Operations snapshot.

Rules verified by focused tests: HTTP 200 without schema-valid parsed records does not start A1-C1; failed, malformed, stale and non-cash results do not replace last-good data; valid-empty restriction data is distinct from failure and is gate-only; unrelated source changes are skipped; the same relevant fingerprint is not processed twice; downstream failure becomes FAILED_STAGE without rolling back the collector save; sourceActivationReady=false, canUnlockConfirmed=false, executable=false and WATCH_WAIT_REJECT remain enforced.

Focused command:
..\.venv\Scripts\python.exe -m pytest tests\test_cash_post_commit_pipeline.py tests\test_market_data_scheduler.py tests\test_source_operations_snapshot.py tests\test_cash_a5_c1.py tests\test_manual_refresh_api.py -q

Result: 38 passed, 1 warning.

Current in-process snapshot: contract trendforge.sourceOperations.v1; 354 compiler contracts; 132 runtime catalog keys; 56 attempted keys; 47 parsed keys; 0 last-good keys; 5 current facts; 5 research-usable facts; cashTrack=null because no current cash last-good artifact was available during verification.

Frontend: node --check passed for source and bundled app.js. The inventory frontend suite is 13 passed and 2 failed because existing tests expect 125 instead of the observed 129 logical keys and an old sector fixture hash. The bundled integrity test still reports manifest index.html size mismatch. The running server checked before restart returned HTTP 404 for the new endpoint; the in-process FastAPI endpoint and focused API test passed.


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

### Commands and observed results

`POST /api/market-data/refresh` completed run `2026-08-16-manual-20260816-123159-0047999505c9`: 123 attempted, 80 `SUCCESS_NEW`, 37 `SUCCESS_UNCHANGED`, 3 `STALE_LAST_GOOD`, 3 `VALID_EMPTY`, 0 terminal fetch failures. Content inspection refined that transport summary to 107 usable parsed sources, 10 status/schema envelopes, 3 stale fallbacks and 3 valid empty.

Focused backend verification: **68 passed** across registry, service, scheduler, manual-refresh API, cash post-commit and Source Operations tests. Original Inventory manual-refresh JavaScript test passed. The bundled integrity test failed at `Size mismatch: index.html`; independent hashing found the six changed files recorded above.

The cash post-commit snapshot was `BLOCKED_INPUT` on 2026-08-16 although `nse_bhavcopy_eod` had 2,463 real rows and `nse_fo_bhavcopy` had 35,089 real rows dated 2026-08-14. The current equality check therefore does not yet satisfy calendar-aware freshness. This observation supersedes the older â€œlive bridge unobservedâ€ note but does not verify a successful A1-C1 live run.

Workbook validation requires: 17 sheets after update, 123 data rows in `CADENCE_AUDIT`, summary counts reconciling to 123, no formula errors, and a rendered `CADENCE_SUMMARY` preview. The workbook remains evidence/audit material and cannot authorize a gate.

## Source repair observation - 2026-08-16

| Source | Observed collector result | Saved latest |
|---|---|---|
| `bse_financial_results_xbrl` | `SUCCESS_NEW`, HTTP 200, structured parser | 9,036 rows, data date 2026-08-15 |
| `bse_shareholding_pattern` | `SUCCESS_NEW`, HTTP 200, structured parser | 5,530 rows, data date 2026-08-15 |
| `mcx_bhavcopy` | `FAILED`; official MCX redirected to Sitefinity status page | last-good retained: 145 rows, data date 2026-08-13 |

The MCX outcome is an external-source availability failure, not a successful current download. The repaired transport rejects 403 pages, Sitefinity status pages and pages without populated `bhavcopy-data`. For BSE, initial live `httpx` calls returned HTTP 200 with `{}` and correctly remained `STALE_LAST_GOOD`. The bounded stdlib browser-session fallback then produced 5,521,181-byte financial and 1,870,413-byte shareholding `Table` payloads; both flowed through the existing strict parser/store path. BSE verification passed **10 focused tests** and **53 service/scheduler tests**; targeted compilation passed. Frontend checks passed **161/161**. The complete backend suite observed **857 passed / 21 unrelated existing failures**; no BSE-focused test failed.



## Calendar-aware Refresh and A1-C1 live verification - 2026-08-16

This supersedes the earlier `BLOCKED_INPUT` observation at the same date. The defect was an incorrect comparison between a Sunday collection date and the latest valid NSE EOD date. `MarketDataScheduler._dispatch_post_commit()` now derives the expected EOD date through `expected_latest_nse_eod_date(at)` and blocks fail-closed when that date cannot be proved.

Live API observation after standard `run_server.py` startup:

- `POST /api/market-data/refresh` completed `2026-08-16-manual-20260816-160551-9e7a3429071a`: 123 attempted, 119 new, 1 last-good fallback, 3 valid-empty and 0 failed.
- `GET /api/source-operations/snapshot` reported `latestDispatch=DISPATCHED`, a completed cash run for `tradingDate=2026-08-14`, A1/A2/A3/A4/A6/C1 completed, A5 skipped for missing current index context, B skipped with `MWPL_MISSING`, and C0 reused.
- Permissions remained fail-closed: `sourceActivationReady=false`, `gateAuthorized=0`, `researchCeiling=WATCH_WAIT_REJECT`, `canUnlockConfirmed=false`, `executable=false`.

Focused tests: 38 passed, 1 warning. Full backend: 861 passed, 21 known unrelated baseline failures. Frontend suite: 161/161 passed. Bundled workbench integrity: 24 copied files verified.

## 2026-08-16 - R1/R2 regression closure and runtime observation

This result supersedes the earlier same-day 21-failure backend baselines.

### Commands

    cd D:\TrendForge\backend
    $env:PYTHONPATH = 'D:\TrendForge\backend'
    D:\TrendForge\.venv\Scripts\python.exe -m compileall -q trendforge_api
    D:\TrendForge\.venv\Scripts\python.exe -m pytest -q --tb=short
    cd D:\TrendForge\frontend
    cmd /c npm test

### Results

| Verification | Observed result |
|---|---|
| Repaired failure-area suite | 107 passed |
| Complete backend | 897 passed, 0 failed, 1 warning |
| Complete frontend | 161/161 passed |
| Inventory snapshot integrity | 24 copied files verified |
| Python compilation | PASS |
| Local API root | HTTP 200 |
| Compiler review | valid; version CROSS-002-2026-08-16-v2; 176 reviewed; 0 gate-authorized |
| R1 evidence API | 123 source records; 2,463 stock records; activation false |
| R2 attention API | 2,463 rows; 1,720 WATCH; 743 WAIT; 0 CONFIRMED; 0 geometry |

### Adversarial behavior retained

- missing official IV calendar returns WAIT_CALENDAR_REQUIRED;
- invalid/weekend/mixed-underlying IV observations cannot enter the 252-session
  window;
- provider PCR payloads cannot override trust or score eligibility;
- malformed date or impossible OHLC candles return schema wait when no valid
  rows remain;
- successful empty, stale fallback and failure remain distinct;
- reviewed source-map drift is detectable through pinned counts and hashes;
- compiler review does not grant activation or gate permission;
- R1/R2 remain WATCH_WAIT_REJECT, non-executable and geometry-free.

The remaining warning is the existing Starlette TestClient/httpx deprecation.
No dependency was installed or migrated in this repair.
## 2026-08-16 - R1/R2 source-specific freshness verification

### Observed behavior

| Verification | Observed result |
|---|---|
| Full registry refresh | 123 attempted; 119 new-data success; 1 stale last-good; 3 valid-empty; 0 failed |
| Refresh manifest | `data/market_data/2026-08-16/snapshots/manual-20260816-201419/manifest.json` |
| R1 freshness policy | `registry-cadence-v1` |
| R1 output | 123 source contracts; 2,463 stock rows |
| R1 freshness | 94 CURRENT; 11 STALE; 18 UNKNOWN |
| R1 usability | 91 USABLE_CURRENT; 3 VALID_EMPTY_CURRENT; 28 STALE_DATA; 1 STALE_LAST_GOOD |
| R2 output | 1,720 WATCH; 743 WAIT; 0 REJECT; 0 CONFIRMED |
| R2 unsafe output | 0 ranked non-current rows; 0 populated entry/target/stop geometry |
| Focused tests | 29 passed, 1 warning |
| Complete backend | 905 passed, 1 warning |
| Complete frontend | 161/161 passed |

### Adversarial cases proved

- Friday NSE EOD data remains current on Sunday when Friday is the expected
  trading session.
- Old daily and weekly data stay visible but cannot be evidence eligible.
- Event sources use fetch recency separately from the date of the latest event.
- Closed-day publishers are not incorrectly forced to the NSE session date.
- Future-dated data and stale valid-empty responses fail closed.
- A stale R1 source cannot retain a WATCH rank or attention priority in R2.
- Changing the freshness-policy version rebuilds completed R1/R2 once; an
  unchanged version remains idempotent.

This verifies research freshness semantics only. It does not activate a source,
authorize CONFIRMED, establish win probability, or enable execution.

## R3 pre-build evidence audit - 2026-08-16

Verdict: VERIFIED WITH BLOCKERS; plan-only, no R3 code built.

Observed:
- resolver implementation exists but is used by fixtures/research paths only;
- selection/r3_claim_adapter.py and selection/r3_live.py are absent;
- /api/v1/selection/resolution is absent;
- A1 persists exact SourceResult and A2 persists exact NormalizedFact lineage;
- run_existing_cash_pipeline holds both exact objects before R1/R2 and is the required adapter boundary;
- compiled contracts with feature IDs or directional permission: 0;
- nse_bhavcopy_eod: no feature IDs, directionalPermission=false, authorityCap=UNSPECIFIED_NO_VOTE, gatePermission=false.

Acceptance consequence:
- do not claim R3 started or complete;
- do not derive claims from generic R1 rows or Workbench samples;
- approve and compile the section 13.9 authority prerequisite before selected live claims;
- require hash-matched storage/API, duplicate-recovery, deterministic R2 builtAt replay, unchanged R2 bytes, and the additional adversarial tests in section 13.9.5.
Focused R3 plan verification: 26 coverage tests passed. Coverage check read 155 rows; R3 has no drift. Eleven unrelated pre-existing drift rows remain: CROSS-001, CROSS-006, CROSS-007, CROSS-014, CROSS-019, CROSS-020, HYBRID-16-2, HYBRID-16-3, HYBRID-16-9, R0 and TDG-GAP-001. Compiler re-observation confirmed zero feature/directional contracts and nse_bhavcopy_eod remains REGISTERED, UNSPECIFIED_NO_VOTE, featureIds empty, directionalPermission false and gatePermission false.
## 2026-08-16 - R3 live resolver verification

| Check | Observed result |
|---|---|
| Feature/compiler contract | Registry 1.1.0, 40 features; only `nse_bhavcopy_eod` has FTR-040 directional permission; zero gate-authorized sources |
| Exact lineage | A1 SourceResult + A2 NormalizedFact factId/date/hash joined to current R1/R2 hashes and permission fingerprint |
| Stale permission | Previous R1 fingerprint rejected; API returned 503 R3_RESOLUTION_NOT_READY |
| Local post-commit replay | R1 2,463 rows; R2 2,463 rows; R3 2,463 rows |
| R3 states | 2,463 WAIT; 0 CONFIRMED |
| Claims | 2,437 selected PARTICIPATION support claims; max one per symbol/correlation group; 0 conflicts |
| Unsafe fields | 0 populated entry, target, stop or quantity fields |
| Activation | sourceActivationReady=false; canUnlockConfirmed=false |
| API | GET /api/v1/selection/resolution returned trendforge.resolution.v1 only after exact hash match |
| Frontend regression | 161/161 passed; Workbench copy integrity remained included |

Adversarial tests prove mixed snapshots, stale permission fingerprints, non-directional/unranked evidence, missing families, API hash mismatch and duplicate missing-R3 recovery fail closed. R2 serialization remains unchanged by R3. Final verification: 67 focused R3 tests passed; complete backend 909 passed with one existing Starlette/httpx deprecation warning; complete frontend 161/161 passed.

Final process observation: localhost API was restarted as PID 3320. `GET /api/v1/selection/resolution` returned HTTP 200 with 2,463 WAIT rows and 0 CONFIRMED. The separate fixture endpoint remained `fixtureOnly=true` with exactly one fixture CONFIRMED decision; it did not enter live R3 storage or output.

## 2026-08-17 - R1/R2/R3 documentation reconciliation verification

| Check | Result |
|---|---|
| Focused R1/R2/R3 regressions | 71 passed; one existing Starlette/httpx deprecation warning |
| Local APIs | R1 evidence, R2 attention and R3 resolution each returned HTTP 200 |
| Current live ceiling | R1: 123 sources / 2,463 stocks; R2: 1,720 WATCH + 743 WAIT; R3: 2,463 WAIT, 0 CONFIRMED, 0 populated geometry rows |
| Short architecture map | Reconciled R1/R2 stale â€œnot builtâ€ language; records live R1/R2/R3 modules and APIs |
| Interactive graph | Live selection node, flow, glossary and node guide reconciled; JavaScript syntax compilation passed |
| Stale wording scan | No `R1/R2/R3 not built` or `partial R1/R2/R3` matches in the updated architecture map, graph or remaining-build navigation |

Browser rendering was not separately observed in this documentation-only pass:
the local browser helper stopped before navigation. That limitation does not
affect the successful JavaScript syntax compilation, but it is not counted as a
visual-runtime observation.## Hybrid V2 paper overlay (research ceiling) - 2026-08-22

```text
pytest path: backend/tests/hybrid_v2 (42 tests)
run: cd D:\TrendForge\backend ; .venv\Scripts\python.exe -m pytest tests/hybrid_v2 -q
plus: tests/test_s4s5_compare.py test_r14_live_ca_join.py test_r5_live_structure.py
      test_r4_live_identity_pin.py test_cash_post_commit_pipeline.py  (90 total green)
frontend: node frontend/tests/acceptance-check.js (166 checks)
schema: trendforge.hybrid-v2-overlay.v1  profile: PRF-HYBRID-V2-OVERLAY
ceiling: RESEARCH_PROXY_NOT_CALIBRATED; canUnlockConfirmed=false executable=false sourceActivationReady=false
GET /api/v1/hybrid-v2/overlay?limit=40 ; GET /api/v1/hybrid-v2/overlay/{symbol}
mismatch/missing -> 503 WAIT_HYBRID_* ; POST -> 405
C1 no CONFIRMED rows ; C2 POST 405 ; C3 lineage mismatch 503, never last-good
C4 WAIT_CA hides AS z ; C5 missing MTO = UNKNOWN not volume proxy
C6/C7 overlay S4 == s4s5_compare within 1e-6 ; C8 kelly <= 0.02, p=0.1 -> 0
C9 S6 UNKNOWN_NEEDS_R12 ; C10 B4 package never changes WITHOUT p-hat
C11 T1 label without R width has no fabricated price ; C12 signal-day-close fill rejected
C13 future available_at never enters AS z ; C14 spine run_hashes unchanged by overlay runs
C15 sourceActivationReady stays false ; C16 numeric scrip / UNKNOWN_ID skip AS
C17/C18 acceptance-check: #s4s5With/#s4s5Without/#s4s5Both kept; #hybridV2Chain + panel exist, no READY live state
```









## R2-B CONFIRMED amendment + guidance OMS - 2026-08-25

text:
pytest path: backend/tests (full) -> 1245 passed, 0 failed
amendment suites: test_r2b_live_named_activation.py + test_s7_state_gates.py + test_guidance_oms.py -> 36 passed
frontend: node frontend/tests/acceptance-check.js -> 212/212
schema: trendforge.guidance-oms.v1 ; named-activation v2 ceiling LIVE_NAMED_ACTIVATION_AMENDED_EOD
G1 amendment pytest 36 passed ; full suite 1245 passed (incl. test_feature_registry after removing an accidental UTF-8 BOM from main.py)
G2 ACTIVATION_OBSERVED (live server 127.0.0.1:8000):
   ready=False authorized=0 confirmedCount=0 -> fail-closed execute SUCCESS
   blockers: nse_bhavcopy_eod R2B_STALE_DATA, nse_corporate_filings_actions R2B_STALE_DATA, nse_index_close_eod R2B_STALE_DATA
   (nse_fno_ban and nse_fo_bhavcopy last-goods are current)
   s7-state mirrors ledger: sourceActivationReady=false, ceiling LIVE_S7_WATCH_WAIT_REJECT_ONLY
G3 NO_ORDERS (place_order absent from s7_state_gates.py)
G4 live POST /guidance-oms/place -> 409 LIVE_ORDERS_ARMED_OFF ; GET /settings/live-orders-arm default all-off (env/lane/ui false)
G5 acceptance-check 212/212 incl. guidance OMS mounts + arm default-off
C1 CONFIRMED unreachable while locked (validator regression kept)
C2 one missing/stale last-good keeps global lock + names blockers
C3 ban/WAIT_CA/blackout/weather/conflict outrank activation_ready
C4 MWPL row can never authorize even when current
C5 sized tickets require side+entry+stop; FLAT requires qty 0
C6 order JSON preview api key REDACTED; real key only inside dispatch
C7 dispatch fires only when env+lane+arm all on (fake transport)


## Full verification session - 2026-08-25 (post ticket 4/4)

text:
Scope: prove nothing built so far regressed (old flows + new amendment).
backend: pytest tests -> 1246 passed, 0 failed (final code state, incl.
         new pit-gate route regression test)
frontend: node frontend/tests/acceptance-check.js -> 212/212
lint: ruff check on all touched files (r2b_live, s7_state_gates,
      guidance_oms + 4 test files) -> All checks passed
live battery (server on 127.0.0.1:8000, real DB):
   script delete/gates_r2b_confirmed_2026-08-25/live_battery.py -> PASS 22/22
   old flows green: named-activation, s7-state (+symbol), scans/latest S8,
      pit-gate, research-quantity, data-lane, ca-join R14, top10 R6,
      evidence-radar, hybrid-v2 overlay, feature-registry + lint ok=true,
      r0b-cohort
   new flow green: guidance-oms GET/preview/place(409 LIVE_ORDERS_ARMED_OFF),
      live-orders-arm round-trip (arm-on still blocked by env+lane; restored off)
   POST guards 405 on named-activation / s7-state / pit-gate
DEFECT found+fixed during battery:
   GET /pit-gate returned 500 - pre-existing NameError in the route
   (called list_latest_selection_payloads without a local import; module
   scope only had the alias). Fixed to match sibling-route import pattern;
   added tests/test_pit_gate.py::test_pit_gate_route_serves_from_store so
   the HTTP route can never regress silently again. TWINS sweep of all
   sibling store-helper routes: every other route imports locally; single site.


## R8 native core scanners verification - 2026-08-25

text:
G1 module: NATIVE_CORE_IDS -> "5 native.breakout.v1,native.trend.v1,
   native.nr_compression.v1,native.rvol.v1,native.volume_thrust.v1"
G2 pytest: tests/test_r8_native_core.py + test_s3_cheap_discovery.py +
   test_s7_state_gates.py -> 46 passed
G2b full backend suite -> 1263 passed, 0 failed (17 new R8 cases)
G3 frontend acceptance-check -> 214/214
ruff on all touched files -> All checks passed
G4 live battery (server 127.0.0.1:8000) -> PASS 24/24, now including:
   GET /api/v1/scanners/definitions -> 200
   GET /api/v1/scanners/native-core -> 200 (computed from live R5 spine)
G5 no place_order under scanners/ -> offenders == []
Observed behavior notes:
   - run identity excludes built_at; stable per lineage (two builds equal)
   - fixture HVBTEST: breakout+trend+rvol matched; thrust unmatched at 2.5x
     baseline (< 3.0 threshold); NR false as computed by R5 engine
   - PK probe failure path: rows byte-identical + PK_SHADOW_UNAVAILABLE warning
   - S6 regression suites unchanged; merge helper covered by unit tests only
     this ticket (production routes inject nothing)


## R10 pipe DSL (FUS-010) verification - 2026-08-26

text:
G1 module: PIPE_IDS -> "2 pipe.breakout_watch.v1,pipe.thrust_participation.v1"
G2 pytest: test_r10_pipes.py + test_r8_native_core.py + test_s3_cheap_discovery.py
   + test_s7_state_gates.py -> 63 passed
G2b full backend suite -> 1280 passed, 0 failed (17 new R10 cases)
G3 frontend acceptance-check -> 215/215
ruff on pipe_dsl.py + tests -> All checks passed
G4 live battery (server 127.0.0.1:8000) -> PASS 26/26, now including:
   GET /api/v1/pipes/definitions -> 200
   GET /api/v1/pipes/pipe.breakout_watch.v1/run -> 200 confirmedCount=0
G5 zero claims / no orders: no EvidenceClaim constructor and no place_order in
   scanners/pipe_dsl.py; PipeRunV1 validator pins confirmedCount=0.
Observed behavior notes:
   - deterministic: two builds on same spine identical (builtAt from R5 batch)
   - twin non-inflation observed: UNION[breakout,trend] out == UNION[breakout] out == 1 on fixture spine
   - INTERSECTION[breakout,nr] drops fixture row; reason SCANNER_NOT_MATCHED:native.nr_compression.v1 recorded (capped 8)
   - ENRICH_S7 in==out always; FILTER_STATE without board -> WAIT_R10_S7_NOT_READY (fail closed)
   - unknown pipe route 404 PIPE_UNKNOWN_ID; POST /api/v1/pipes/run 405

## R11 MCX master readiness verification - 2026-08-25

text:
G1 import: trendforge.mcx-master.v1 LIVE_MCX_WAIT_WITHOUT_NAMED_ACTIVATION
G2 pytest: test_r11_mcx_live.py + test_s7_state_gates.py +
   test_s5_shortlist_enrichment.py -> 41 passed
G2b full backend suite -> 1291 passed, 0 failed (11 new R11 cases)
G3 live: GET /api/v1/selection/mcx-master -> 200 confirmedCount=0
   (battery probe; honest WAIT_* on the real DB)
G4 frontend acceptance-check -> 216/216
ruff on r11_mcx_live.py + tests -> All checks passed
Observed behavior notes:
   - empty spine: ready_count=0, warnings carry WAIT_MCX_MASTER,
     tried_source_keys includes mcx_contract_master + mcx_market_watch +
     mcx_bhavcopy
   - master rows with missing lot/tick stay WAIT (WAIT_LOT/WAIT_TICK), no
     invented numbers; GOLDM full fields flow through with dte computed
   - tender window hit -> WAIT_TENDER veto, row excluded from READY
   - fresh fbil_usdinr_reference + cftc_cot parses do NOT change readiness or
     confirmedCount (context-only law)
   - S7 cash suites green after build (CONFIRMED law unchanged)

## R15 Scanner Lab UI verification - 2026-08-25

text:
G1 frontend acceptance-check -> 217/217
G2 LAB_WIRED (scanner-lab.js + adapter both expose TrendForgeScannerLab;
   Combined_Score absent from lab)
G3 test_s7_state_gates.py -> 19 passed (CONFIRMED law unchanged)
G4 test_r15_lab.py -> 3 passed (bundle one-200, POST 405, pinned counters)
G5 full backend suite -> 1294 passed, 0 failed
G6 live battery -> PASS 28/28 incl. GET /api/v1/scanners/lab-bundle -> 200
   confirmedCount=0
Production-grade flow re-check (all 200 or named codes):
   s7-state, scans/latest, scanners/native-core, pipes run, mcx-master,
   pit-homework route family, guidance-oms/{symbol} - green in battery.
All Stocks column freeze: exact radar <th> template asserted unchanged; new
lab owners forbidden from emitting <th>.
Defect fixed en route: research-quantity row-error path used undefined
SelectionState/EvidenceDirection (would NameError instead of degrading to a
WAIT row); imports added and ruff F821 sweep confirms no remaining sites.

## R13 remaining scanners verification - 2026-08-26

This record is superseded by the 2026-08-27 correction below; its 1306 and
29/29 counts and RSI/close-range formula descriptions are not current.

## R13 guidance-grade closure verification - 2026-08-27

```text
Focused R13/R8/R15/S8 integration: 60 passed
Former R10 deterministic regression + focused suites: 61 passed
Full backend: 1320 passed, 0 failed, 1 Starlette deprecation warning
Frontend acceptance: 217/217
Python + JavaScript compilation: PASS
Read-only live battery: PASS 24/24
```

Observed localhost behavior on the real current universe:

- `/api/v1/scanners/definitions`: 200, 11 definitions including all six R13 ids.
- `/api/v1/scanners/native-core`: 200, 2,623 rows, 2,379 matched rows,
  `confirmedCount=0`, additive candidate-relationship and lineage fields.
- `/api/v1/scanners/lab-bundle`: 200, full `nativeCore`, no error code,
  `confirmedCount=0`.
- `/api/v1/selection/scans/latest`: 503 `WAIT_S8_LINEAGE`; stale prior lineage
  was not relabelled current. Normal future daily builds now attach the native
  run hash and representative guidance ids.
- Observed latency: native-core about 14-19 seconds; lab bundle about 32-34
  seconds. Bulk query count is one; no per-symbol fallback exists.
- No dependency, database migration, broker call, order, quantity, entry,
  target, stop or win-probability feature was added.
## R16 pre-migration verification - 2026-08-28

| Check | Observed result |
|---|---|
| Focused R16/pipeline/scanner tests | 51 passed |
| Complete backend | 1,336 passed; 0 failed; one Starlette deprecation warning |
| Complete frontend | 218/218 passed |
| R16 CLI against current live DB | BUILDING / PIT_NOT_APPROVED / WAIT_R16_SCHEMA_NOT_APPLIED |
| GET /api/v1/selection/pit/status | 200; contract v2; six missing R16 tables named |
| GET /pit/runs, /pit/observations, /pit/metrics, /pit/approval | 200; zero persisted R16 rows; same schema blocker |
| POST /api/v1/selection/pit/status | 405 |
| Initial browser network | PIT status and metrics loaded; observations did not load initially |

Adversarial coverage includes post-cutoff input rejection, exact-cell identity,
outcome taxonomy, conservative same-bar handling, policy floors, read-only GET
behavior, unsupported POSTs, shared S8 lineage, bounded symbol/date history
loading, and same-date conflicting S8 payloads failing closed. The legacy PIT
compatibility payload exposes canonical validationStatus plus a read-only
guidanceStatus alias; it does not restore client authority.

Observed limitations:

- migration 0013_r16_pit_substrate was not applied to the live database;
- no real R16 dataset, hypothesis, observation, fold, metric or approval row was
  created;
- no sufficient prospective S8 history was established;
- replay hashes, query plans, incremental latency, restart/concurrency and
  backup/restore were not observable on populated live state;
- browser toggle interaction was not run because the action approval service
  was unavailable, although the lazy path is acceptance-tested and initial
  no-observation network behavior was observed.

Verdict: pre-migration implementation VERIFIED WITH CAVEATS; full
R16_IMPLEMENTATION_VERIFIED and PIT_APPROVED are not established.


## R16 post-migration validation - 2026-08-29

| Check | Observed result |
|---|---|
| Online pre-migration backup | `integrity_check=ok`; 5,832,974,336 bytes; 1,424,066 pages x 4,096 bytes |
| Migration | `0013_r16_pit_substrate` applied; six PIT tables and worker state present |
| Database integrity | `quick_check=ok`; no foreign-key errors; existing non-R16 schema unchanged |
| Current S8 | 678 rows; 2026-08-28; real S2/S3 lineage; no missing stages; completeness 1.0 |
| Official S2 companion | 165 populated parsed rows for 2026-08-28; HTTP success alone was not accepted |
| Catch-up | one dataset; 2,034 hypotheses; 2,034 latest observations; six metrics; six ledger rows |
| Repeated replay | two runs appended zero observations; counts and revision hash unchanged |
| Runtime authority | BUILDING / PIT_NOT_APPROVED / DATASET_AND_REPLAY / INCONCLUSIVE; all three authorization flags false |
| API battery | five GETs returned 200 and did not mutate counts; five POST variants returned 405 |
| Query plans | observation dataset/latest and exact-cell metrics use named `idx_pit_*` indexes |
| Focused R16 | 16 passed; one Starlette deprecation warning |
| Complete backend | 1,343 passed; zero failed; one Starlette deprecation warning |
| Complete frontend | 218/218 passed |

The replay revision is
`7a0ba5a05c9a535ea64f424d6bc1c02e2840c5986a4271d64ed94df28030e0cc`.
The populated database contains 1 dataset run, 2,034 hypotheses, 2,034
observations, 0 folds, 6 metrics, 6 approval-ledger rows and 1 worker-state row.
Zero folds are expected with one eligible date and are an approval blocker, not
a successful performance result.

Adversarial behavior observed: incomplete/stale S8 artifacts are rejected
before same-date conflict grouping; valid conflicting complete S8 runs still
fail closed; repeated replay is append-only and idempotent; GET does not replay
or approve; missing history does not fabricate folds, confidence, probability,
CONFIRMED, quantity or execution.

Rendered inspector observation could not be rerun because the in-app browser
runtime exited on a Windows sandbox-helper error. Frontend acceptance proves
that initial load requests status/metrics only and observations are lazy-loaded
on inspector open. Therefore R16 implementation is verified with this UI
observation caveat, while `PIT_APPROVED` and production readiness remain false.




## CROSS-015 / TDG-GAP-022 tradability validation - 2026-09-03

| Check | Result |
|---|---|
| Focused tradability + S7 + S8 tests | 53 passed; one Starlette deprecation warning |
| Complete backend regression | 1,474 passed; zero failed; one Starlette deprecation warning |
| Complete frontend regression | 220/220 passed |
| Requirement coverage | 155 rows; zero drift; CROSS-015 and TDG-GAP-022 IMPLEMENTED / TESTED_OFFLINE |
| Policy coverage | NSE intraday, NSE swing/event and MCX profiles |
| Hard precedence | REJECT > WAIT > PASS |
| Non-voting law | PASS cannot vote, confirm or unlock CONFIRMED |
| Adversarial states | missing, stale, malformed, conflicting and valid-empty fail closed where required |
| Symbol restrictions | inactive security, T2T intraday, high ASM/GSM/ESM, F&O ban, locked band, halt and auction paths covered |
| S8 lineage | Tradability run hash, result hash, component reasons and payload preserved |
| API mutation boundary | GET-only projection; POST returns 405 |
| Pre-acquisition direct-source observation | INFY and TATASTEEL returned WAIT; T2T/ASM/GSM/market-status/security-master stale; ESM/price-band were missing; run hash `c9a29cb600d429c538c70819cbcb9328d5fa5060ec88e71428c79d05f1e15c1e` |
| Current full S7 HTTP observation | 503 `R5_STRUCTURE_NOT_READY`; no stale or fabricated S7 result returned |

This first pass proved the gate implementation and fail-closed integration but
did not yet prove ESM, price-band or auction acquisition. The follow-up below
supersedes only that acquisition limitation.

### Acquisition follow-up - 2026-09-03

| Check | Observed result |
|---|---|
| Registry compile | 126 pinned jobs; source-map v3: 157 named inventory, 135 runtime catalog, 179 living entries, 22 runtime-only, zero gate-authorized |
| `nse_esm` live last-good | `POPULATED`; 290 rows; data date 2026-09-03 |
| `nse_price_bands` live last-good | `POPULATED`; 3,517 rows; data date 2026-09-02 |
| `nse_auction_securities` live last-good | `VALID_EMPTY`; explicit `NIL`; zero securities; data date 2026-07-09 |
| Collector-to-gate bridge | Canonical `MarketDataStore` normalized last-good is read before legacy parser-output fallback; corrupt canonical identity is `MALFORMED` |
| Valid-empty separation | Auction XLS integrity-member records are not mistaken for securities when parser output says `validEmpty=true` |
| Price-band boundary | Percentage/classification is retained; absent exact lower/upper values yield WAIT, never PASS-by-assumption |
| Focused acquisition/registry/compiler/tradability tests | 67 passed |
| Complete backend regression | 1,485 passed; zero failed; one Starlette deprecation warning |
| Complete frontend regression | 220/220 passed |

This supersedes only the earlier statement that these three acquisition paths
were unproved. It does not supersede historical run counts or the upstream
`R5_STRUCTURE_NOT_READY`, source-activation, PIT, broker or execution ceilings.
