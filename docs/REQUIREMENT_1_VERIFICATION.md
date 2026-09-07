# Requirement 1 verification: current state versus history

Review date: 2026-09-07. Scope: documentation and UI provenance only.
Baseline: `e2d501b793c6f329d91c65399255dace5b9acc8a`.

## Observed local results

Environment: Python 3.13.5 and Node 22.16.0; not the repository's pinned CI environment.

| Command / check | Observation |
|---|---|
| Baseline `cd frontend && npm test` | Passed; acceptance checker 220/220, plus the other configured suites. |
| New `node frontend/tests/status-provenance.test.js` before implementation | Failed as expected: missing status-provenance.js. |
| New provenance test after implementation | Passed: snapshot/fetch timestamps, stale retention, UNKNOWN, lineage, escaping and non-mutation. |
| `node frontend/tests/scan-history.test.js` | Passed: GET-only, empty, failure, schema, exact ID, escaping and racing responses. |
| `node frontend/tests/selection-provenance-integration.test.js` | Passed: missing S7, mismatched lineage, retained snapshot, cleared old panels, and recovery. |
| Existing frontend suites after wiring | Passed; acceptance checker 220/220 and all configured suites. |
| Baseline `cd backend && python -m pytest -q` | 1466 passed, 17 failed, 2 skipped in this environment. Failures include engine-version mismatches and unavailable pyarrow. These failures existed before requirement 1 edits. |

The local baseline must not be described as all-green. Pinned Python 3.14 CI is
the separate complete regression check. Its actual result will be attached to the
branch/PR; no future passing result is assumed by this document.

## Boundaries checked

No backend business logic, source registry, File A public state, model approval,
migration, credentials or execution code changed. Current and saved-history UI
renderers remain separate. History performs no POST and never calls /scans/latest.
R5 v1/v2 display compatibility does not change R5 calculations or acceptance ceilings.
Original historical documentation is retained after explicit history boundaries.

## Not established by these tests

The user's local database state, current source freshness, live broker login,
PIT/model approval, end-to-end live data availability and order execution were not
tested or authorized. Other review findings, including the backend tradability
timestamp-field defect, duplicate scan orchestration and the mypy baseline,
remain separate stages and are not claimed fixed here.