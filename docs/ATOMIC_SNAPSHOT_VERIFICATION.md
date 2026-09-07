# Atomic research snapshot: observed verification

Date: 2026-09-07. Scope: one consistent selection refresh, not all repository errors.

Tested application revision: `fdfafdd3601f2366741a4b217cf33edc00dde599`.
Branch: `fix/atomic-research-snapshot`.
PR #2 targets `fix/current-state-history`, preserving the preceding work.
This later evidence-only commit changes no application code. Main is unchanged.

## Results

| Check | Observed result | Evidence |
|---|---|---|
| Focused backend | 43 passed | Local Python 3.13.5; cash post-commit, snapshot, read-transaction and S8-service tests |
| Complete backend regression | Passed | GitHub CI 34149674933, backend job 101829106242 |
| Ruff | Passed | Same backend job, Ruff step |
| Complete frontend | Passed | CI 34149674933, frontend job 101829106468; 220/220 acceptance checks and existing/new suites |
| Python compilation and whitespace | Passed | Local compileall and git diff --check |
| Desktop/mobile browser | Passed | UI run 34149674928; artifact 10028904375 |
| Python type-checking | Failed, non-blocking | CI 34149674933, job 101829106444; not represented as green |

Local focused command:

```sh
cd backend
python -m pytest tests/test_cash_post_commit_pipeline.py tests/test_research_snapshot.py tests/test_read_snapshot.py tests/test_s8_service.py -q
```

Hosted browser report (synthetic data only):

```json
{
  "pageErrors": [],
  "requestCount": 38,
  "snapshotRequests": 2,
  "legacySelectionRequests": [],
  "source": "SYNTHETIC_ONLY"
}
```

Two snapshot requests mean initial load plus one deliberate refresh: one per
selection refresh. The total of 38 includes independent context/control/history
requests, not 38 calls to the new snapshot endpoint. Mobile document and viewport
widths both measured 390px, and the hidden inventory drawer remained hidden.

## What these checks establish

Concurrent writes do not change a pinned read view mid-request. R1/R2 or
downstream mismatches do not get combined into a current decision. Nested readers
cannot write, initialize schema, commit or release the owner's transaction.
The shared scan is assembled once; dependent panels reuse its results. Late
browser responses cannot replace newer ones. Saved history remains separate.

## Remaining boundaries

The Python type-check job still fails. This stage does not certify that every
reported typing issue is old or that every repository defect is repaired.
Separate backend defects and full collector publication atomicity are outside
this requirement. Partial publication is detected, not silently mixed.
Read consistency does not establish market freshness, broker connectivity,
PIT/model approval, profitable signals, or production authorization.
No broker request, live order, live data refresh or production migration was run.

This record supersedes the pre-CI pending-verification notes for this stage in
BUILD_STATUS, VALIDATION and the initial PR description; it does not overwrite
their historical observations.
