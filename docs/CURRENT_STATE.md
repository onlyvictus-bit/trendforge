# Current code and readiness snapshot

**Reviewed:** 2026-09-09. **Previous reviewed checkpoints preserved:** 2026-09-08 and 2026-09-07. **Code baseline:** R-HIST-03C on `feat/rhist03-producer-wiring` (PR #6), stacked on retention branch `fix/retention-evidence-safety` and TF-01 `19a8c762314cdb7b54556c17c8ae5a46ad7325e8`.
**Role:** current navigation and evidence summary, not a new plan, source registry,
activation authority, or production certification. File A retains build order,
public-state definitions and acceptance ceilings. Read this page before dated
entries in BUILD_STATUS, VALIDATION, architecture notes or remaining-build guides.

## PR #6 repair under validation - 2026-09-10

An isolated local patch based on PR head `6de1e14973edcf62b61c9b6a1441214ace656ec4`
repairs the three CI failures and implements controlled immutable supersession
and finalizer/registration crash/concurrency protection. The original 03C
checkpoint below remains historical evidence, not the status of the new patch.
See [the execution record](fable/RHIST03D_PR6_REPAIR_2026-09-10.md) and the newest
VALIDATION entry. Final local regression passed: 1699 tests, zero failures/skips;
compile, Ruff and frontend passed; normalized Mypy delta versus 03C is zero.
Exact-head GitHub CI after publication is pending. 03D is IN PROGRESS; 03E/03F remain LOCKED; LIVE-DATA-VERIFIED and
PRODUCTION-ACCEPTED remain NO. No live migration or authority change occurred.

## R-HIST-03C implementation checkpoint - 2026-09-09

The existing NSE cash EOD R16 producer now freezes hypotheses against an exact,
protected S8 publication ID, artifact version, lineage hash and full payload
seal. Decision inputs come only from that parent's original hash-bound evidence,
not a later raw-bar query. Outcome observations and explicit source/outcome/
interpretation revisions are immutable, separately timed records. Rebuilds link
new decision versions to their original versions rather than replacing them.

The existing retention publication/outbox/authority owns DECISION_VERSION,
OUTCOME and REVISION protection. Canonical artifact and intent writes share one
transaction; governed readers require PUBLISHED proof and perform no retention
writes. WAIT/WATCH/REJECT/no-entry/expired and other non-trade history remains
represented. Ambiguous stop/target collisions do not become certain losses in
metrics. This is historical integrity, not intraday activation or PIT approval.

R-HIST-03A/B were tested before this slice. The 03C local gate and commands are
recorded in VALIDATION; exact PR-head CI acceptance is recorded separately on
PR #6 and must be checked for the revision being reviewed. R-HIST-03D/E/F and the
full R-HIST-03 gate remain open. R-HIST-04 remains plan-only. No live dataset was
validated and no production, model, strategy or execution permission was added.

Deployment requires the explicit additive `r16-schema --apply` command described
in BUILD_STATUS. Legacy S8 rows without their original full-payload seal are NOT
silently backfilled or accepted; legacy R16 rows without publication proof are
preserved in storage but excluded from governed reads. Missing proof fails to a
WAIT_RHIST03 reason. A future provenance-verified repair is a separate operation,
never a read-time reconstruction from current data.

## Current refresh contract

The primary refresh uses one **atomic research snapshot** endpoint with 26
panel payloads (the original 22 plus dependent weather/radar/top-10/comparison
rooms). It is a single SQLite view, not a guarantee of live prices or a
historical backtest cutoff. All current gates share the response capture time;
original R1/R2/R5 timestamps remain visible separately. Mismatched core lineage
fails closed, and absent optional panels carry explicit reasons.

The response's S8 object is an unpersisted projection. Existing post-commit and
explicit persistence paths still own saved history. The named-source R2-B
observation write occurs on the post-commit path so refreshing a screen cannot
write a ledger. Trading rules, source-proof requirements and execution controls
are not replaced by this transport contract. See
[ATOMIC_RESEARCH_SNAPSHOT.md](ATOMIC_RESEARCH_SNAPSHOT.md) for implementation and
verification. Unrelated legacy typing and individual-route defects remain open.

## Eight independent questions

| Question | Evidence owner | What must not be inferred |
|---|---|---|
| Is code implemented? | Modules, routes, renderers and their tests at the inspected revision | File existence does not prove runtime readiness. |
| Did tests pass? | A dated test run with command, environment, revision and results | An old green run is not today's green run. |
| Was real data observed? | Source records and hashes for a named observation | HTTP 200 and fixtures do not prove usable market data. |
| Is source data fresh? | Source/calendar policy evaluated at the decision timestamp | A recent browser fetch does not make an old snapshot fresh. |
| Is research activation allowed? | Current matching S7/R2-B response and gates | Implementation, history and source counts cannot set activation. |
| Is PIT validation approved? | R16 status and approved evaluation evidence | Accumulated rows do not themselves mean PIT_APPROVED. |
| Is a model approved? | R18 governance evidence | Tests, schema presence or model files do not mean MODEL_APPROVED. |
| Is execution authorized? | Separate existing execution controls | None of the preceding answers grants order authority. |

No single `complete`, `ready`, or percentage-complete field replaces these questions.

## Implementation checkpoint (not a live database observation)

| Area | Code at the reviewed baseline | Last recorded observation / remaining boundary |
|---|---|---|
| Collection and cash preparation | Existing collector/store and `selection/cash_post_commit.py` chain source commits through cash preparation and R1/R2. | Current source freshness must be evaluated from runtime records; no live refresh was performed for this requirement. |
| Identity and EOD structure | R4, R14 and R5 implemented; R5 requires matching corporate-action lineage. R5 schema is `trendforge.structure-batch.v2`. | WAIT/REJECT research ceiling; implementation is not source activation. |
| Research assembly | `selection/s8_service.py` connects S3, native guidance, weather, tradability and S4-S7 into saved S8 research. | Individual prerequisites can block the run. The older CLI assembler remains a separate follow-up issue. |
| Final research state | `selection/s7_state_gates.py` owns public research classification. | Named PRF-003 EOD activation exists but must be observed; no activation setting changed here. |
| Tradability | `selection/tradability.py` is implemented and integrated. | Price-band geometry/data-operation gaps and the separately identified API timestamp defect are not closed by retention work. |
| Historical retention | R-HIST-01/02 authority and cleanup protection, 03A outbox, 03B exact S8 roots, and 03C R16 outcome/revision wiring exist on PR #6. | Exact-head gates are separate from local checks. ML/model/profile/audit producers (03D), registry/coverage (03E), complete fault acceptance (03F), archival, live-data reconstruction and production acceptance remain open. |
| R16 PIT | Dataset/replay/label/metric/storage/service code and UI exist. | 2026-09-01 recorded only one complete S8 date and PIT_NOT_APPROVED. That is a dated observation, not today's database count. |
| R18 governance | `r18_governance.py`, `r18_store.py`, `r18_service.py` and the Paper/ML renderer exist. | 2026-09-02 recorded MODEL_NOT_APPROVED and WAIT_R18_SCHEMA_NOT_APPLIED. Do not rebuild R18 merely because older notes say it is absent. |
| OpenAlgo / intraday | R17 fixture-verified read-only shadow components exist. | R9 and R17-G were postponed in the 2026-09-01 handoff. A working live broker session was not observed in this review. |
| Order guidance | Existing preview and separately guarded dispatch code remain unchanged. | Retention work neither tests a live order nor adds, arms or authorizes execution. |

Status observations above are sourced from the explicitly dated entries retained
in [BUILD_STATUS.md](BUILD_STATUS.md), [VALIDATION.md](VALIDATION.md), the retention plan, and the
module references. They must be re-observed before being described as current runtime state.

## UI meaning after requirement 1

`status-provenance.js` is a presentation-only projection of existing responses.
It performs no acquisition, database migration, scoring, source activation or order call.

| Display mode | Meaning |
|---|---|
| FIXTURE | Demonstration values. Current market evidence has not been loaded. |
| LOADING | A refresh is pending; retained values are not revalidated. |
| SNAPSHOT | A stored R1/R2 research response was received. Not a live quote. |
| STALE | A refresh failed after a previous success; original timestamps remain visible. |
| HISTORICAL view | A separately selected immutable S8 run. Never replaces current selection, activation or quantities. |
| UNKNOWN status | Response absent, failed, malformed or lineage-incompatible. Not a fabricated approval or rejection result. |

These labels are **presentation metadata**, not additional public trading states.
WATCH / WAIT / CONFIRMED / REJECT remain backend-owned and unchanged.

The provenance panel distinguishes decision as-of time from response-received time.
Stored row freshness flags are labelled as measured at snapshot creation, not re-evaluated
by the browser. S7/S8/PIT panels clear on missing responses; optional request failures remain
inspectable. S7 activation and latest S8 metadata must match the loaded R2 lineage.
An older saved run, even if it was once valid, cannot authorize a current trade.
Missing PIT/model status is UNKNOWN; missing numeric historical metrics are
UNAVAILABLE rather than zero. The legacy header news examples remain labelled fixtures.

Header **History** uses only `GET /api/v1/selection/scans?limit=100` and
`GET /api/v1/selection/scans/{run_id}`. It does not call the build-on-read
`/scans/latest`, collector refresh, or any write endpoint. The existing M-Factor
history demonstration remains explicitly labelled FIXTURE HISTORY. The header
date displays the loaded snapshot date and is not an unimplemented historical-query control.

## Validation and update discipline

See [REQUIREMENT_1_VERIFICATION.md](REQUIREMENT_1_VERIFICATION.md) for observed
commands and limitations. This page deliberately does not embed a permanent test-pass badge.
CI test success, broker connectivity, database readiness and trading permission are different claims.

For each later milestone, update this snapshot with code evidence and an explicit
review date; append test observations to the verification/build logs. Preserve
older entries as history. Never delete contradictory old evidence merely to make
the current summary look cleaner. `present.md` and dated gate/audit reports remain
historical evidence, not current build instructions.

---

## TF-01 safety checkpoint — 2026-09-08

**Base:** `docs/trendforge-system-brain` at `62307eb237731e71dda20cb9216fff281ab7ebcf`.
**Pinned pre-commit verifier:** GitHub Actions run `34255614854`.

TF-01 changes the safety contract in two places without activating execution:

- Generic macro collection state `RESEARCH_ONLY` no longer proves an event blackout is clear. S7 now requires an exact instrument/symbol/profile/version `EventClearanceResult`; missing, expired, metadata-only, incomplete, wrong-scope or contradictory evidence fails closed. Only current lineage-backed semantic `CLEAR` can satisfy the mandatory event gate.
- Required upstream resolver gates remain typed through S6 as `inherited_gates` and are structurally enforced by S7. `PIPELINE_MANDATORY` gates propagate; S6-local activation/profile ceilings remain diagnostic/local and optional evidence does not become a permanent downstream blocker.

Observed pinned verification for the corrected candidate before the final commit:

| Check | Observed result |
|---|---:|
| Focused macro/S6/S7/S8/TF-01 chain | **79 passed, 2 warnings** |
| Full backend regression | **1,527 passed, 2 warnings** |
| Ruff | **Passed** |
| Mypy | **513 errors in 70 files; 266 source files checked — unchanged from TF-00 baseline** |
| Frontend | **220/220 passed** |
| Compile/import checks | **Passed** |
| Diff / execution-authority scan | **Passed; no live-order authority added** |

Status at this checkpoint:

- **IMPLEMENTED:** YES — this TF-01 commit contains the scoped event-clearance and typed-gate contract changes.
- **TESTED:** YES — pinned pre-commit verification passed; exact final PR-head CI must still be observed separately.
- **LIVE-DATA-VERIFIED:** NO — no production/live event feed acceptance is claimed here.
- **PRODUCTION-ACCEPTED:** NO at commit creation — exact final-head CI and the documented stage-acceptance review remain required.

The existing TF-00 Mypy risk-classification work, A07 and other unrelated baseline defects are not silently closed by TF-01. No broker/order activation, arm switch or live execution authority is changed.

---

## R-HIST historical-retention checkpoint — 2026-09-08

**Detailed authority and roadmap:** [HISTORICAL_DATA_RETENTION_AND_ML_MEMORY_PLAN.md](HISTORICAL_DATA_RETENTION_AND_ML_MEMORY_PLAN.md)  
**Branch:** `fix/retention-evidence-safety`  
**Base:** TF-01 exact head `19a8c762314cdb7b54556c17c8ae5a46ad7325e8`

Purpose: preserve the exact point-in-time evidence required to reproduce decisions, outcomes, backtests and future ML datasets. The governing rule is **Delete copies, not history.** Age determines storage tier; evidence references determine deletability.

### R-HIST-01

- `HistoricalRetentionAuthority`: IMPLEMENTED
- HOT/WARM/COLD policy: IMPLEMENTED
- durable evidence classes: IMPLEMENTED
- immutable reference IDs: IMPLEMENTED
- date/run/hash validation: IMPLEMENTED
- transitive protection: IMPLEMENTED
- protected-evidence disappearance detection: IMPLEMENTED
- fail-closed deletion assertions: IMPLEMENTED
- adversarial unit tests: IMPLEMENTED
- prior exact-head backend/Ruff/frontend CI: PASSED

### R-HIST-02

The real `MarketDataStore.cleanup_retention()` is now wired to the authority. Protected dates and hashes are removed from ordinary expiry/object-GC eligibility; candidate date/run/hash deletions are checked against the authority; protection is resolved again before destructive mutation; changed or corrupted lineage fails closed.

Adversarial integration tests now cover decision protection, ML-hash transitive protection, temporary expiry, disappeared protected lineage, cleanup-time protection changes and preservation of legitimate unprotected deletion.

Current R-HIST-02 status at this documentation commit:

- **IMPLEMENTED:** YES
- **TESTED:** PENDING exact final-head CI
- **LIVE-DATA-VERIFIED:** NO
- **PRODUCTION-ACCEPTED:** NO
- **LIVE ORDER AUTHORITY:** unchanged / NO new authority

Still open and must not be inferred complete:

- R-HIST-03 automatic producer registration for decisions/outcomes/revisions/ML/model/profile/audit evidence
- R-HIST-04 HOT -> WARM -> COLD/archive movement with hash-verified transfer
- R-HIST-05 point-in-time ML dataset builder and leakage audit
- R-HIST-06 complete opportunity/outcome/failure memory
- R-HIST-07 real-data reconstruction, whole-system PIT replay/backtest, leakage testing and final acceptance

The legacy five-day setting is therefore no longer allowed to override a durable active evidence reference, but it is **not** the desired final historical lifecycle. R-HIST-04 must replace simple aging with tiered movement/archive semantics.
