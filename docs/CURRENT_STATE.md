# Current code and readiness snapshot

**Reviewed:** 2026-09-07. **Code baseline:** `e2d501b793c6f329d91c65399255dace5b9acc8a`, plus the current/history presentation changes and the atomic-snapshot stage.
**Role:** current navigation and evidence summary, not a new plan, source registry,
activation authority, or production certification. File A retains build order,
public-state definitions and acceptance ceilings. Read this page before dated
entries in BUILD_STATUS, VALIDATION, architecture notes or remaining-build guides.

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
| Tradability | `selection/tradability.py` is implemented and integrated. | Price-band geometry/data-operation gaps and the separately identified API timestamp defect are not closed by documentation work. |
| R16 PIT | Dataset/replay/label/metric/storage/service code and UI exist. | 2026-09-01 recorded only one complete S8 date and PIT_NOT_APPROVED. That is a dated observation, not today's database count. |
| R18 governance | `r18_governance.py`, `r18_store.py`, `r18_service.py` and the Paper/ML renderer exist. | 2026-09-02 recorded MODEL_NOT_APPROVED and WAIT_R18_SCHEMA_NOT_APPLIED. Do not rebuild R18 merely because older notes say it is absent. |
| OpenAlgo / intraday | R17 fixture-verified read-only shadow components exist. | R9 and R17-G were postponed in the 2026-09-01 handoff. A working live broker session was not observed in this review. |
| Order guidance | Existing preview and separately guarded dispatch code remain unchanged. | This requirement neither tests a live order nor adds, arms or authorizes execution. |

Status observations above are sourced from the explicitly dated entries retained
in [BUILD_STATUS.md](BUILD_STATUS.md), [VALIDATION.md](VALIDATION.md), and the
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