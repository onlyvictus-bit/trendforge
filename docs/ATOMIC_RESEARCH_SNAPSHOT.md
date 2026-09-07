# Atomic research snapshot contract

Requirement: replace the selection adapter's 22 independent latest reads with
one coherent, read-only response. Builds on the current/history presentation
work; File A remains the only state, source-authority and strategy owner.

## Design and acceptance gates

1. `GET /api/v1/selection/snapshot` captures ONE SQLite read transaction in the
   existing database. Storage and canonical market-data reads borrow that same
   connection. No database copies, new downloader, migration, ledger writes or
   saved-scan writes are permitted during a snapshot request.
2. Match R1/R2 identities, hashes, collector and permission fingerprints. Match
   R4/R14/R5 to those exact parents. A partially published new generation cannot
   be mixed with an old generation. Core mismatch returns a named 503; optional
   missing stages have explicit per-panel errors.
3. Reuse the S8 service's assembly once: S3, native guidance, weather, S4, S5,
   S6, S7 and tradability. Share those outputs with scanner pipes and quantity
   projections. Do not call build-on-read HTTP endpoints from the new service.
4. One response ID/hash covers the returned panel set. Decision-as-of and
   capture time remain distinct. All newly evaluated gates use one captured-at
   time; the persisted R5 decision time remains source provenance, not a claim
   that a new evaluation occurred historically. Control/settings observations are labelled
   separately; database consistency does not prove data freshness or approval.
5. The frontend requests only this endpoint for its selection refresh, validates
   the complete envelope before rendering, rejects stale response generations,
   and keeps history separate. No fallback to the 22 old reads.
6. Verify concurrent writer commits, read-only enforcement, cleanup on failure,
   missing/mismatched lineage, one assembly per request, absence of GET writes,
   frontend request counts, overlapping refreshes, and synthetic browser flow.
7. Prevent indirect second fetches: native/MCX/pipes/Hybrid/activation/guidance
   listeners consume the already received bundle. Weather, top-10, radar and
   S4/S5 comparison are included as separate context panels (26 total). Scanner
   Lab's explicit Refresh refreshes the shared snapshot; its tabs remain local.
8. The existing R2-B proof builder runs on cash post-commit before S8 and records
   a hash-matched observed ledger there. Read-only refresh rechecks that ledger;
   it never promotes missing, changed or obsolete proof, nor writes records.

### Limits

The SQLite view is request-scoped, not a permanently cached global connection.
Read budget is 30 seconds; browser request budget is 45 seconds. A timeout or
missing database produces an unavailable response, never fallback to 22 reads.
Browser cancellation prevents late replacement; it is not a guarantee that an
already running server thread instantly stops. No inter-request memoization is
claimed. Context and runtime controls are explicitly scoped, not extra votes.
Hashes cover the serialized envelope; independent data freshness still requires
source/calendar policy. This does not prove atomic publication by the collector:
partially published generations are detected and reported rather than combined.


Legacy individual routes remain compatible for direct inspection. This does not
claim to repair their separate defects, all repository typing debt, or every
other page's independent research tools. Tests do not authorize a live trade.

## Verification

Local isolated checkout (Python 3.13.5 / Node 22):

- `cd backend && python -m pytest tests/test_cash_post_commit_pipeline.py tests/test_research_snapshot.py tests/test_read_snapshot.py tests/test_s8_service.py -q`: **43 passed**.
- `cd frontend && npm test`: **passed**, including **220/220** existing acceptance checks, the previous history/provenance suites and the new atomic-snapshot race/validation suite.
- `python -m compileall -q backend/trendforge_api backend/tests scripts/verify_requirement1_ui.py`: passed.
- `git diff --check`: passed.
- Local Chromium: navigation blocked by environment policy (`ERR_BLOCKED_BY_ADMINISTRATOR`); not claimed passed.

Pinned Python 3.14 full regression, Ruff and hosted desktop/mobile browser checks
are pending observation. Repository-wide mypy debt is not claimed fixed by this
requirement. Acceptance results will be recorded with their exact CI revision.
No real broker, live source freshness, production database or live order was
validated by the synthetic fixtures.