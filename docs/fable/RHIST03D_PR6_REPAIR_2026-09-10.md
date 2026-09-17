# PR #6 repair execution record

This record continues `../R-HIST-03D_IMPLEMENTATION_SAFETY_AND_REPAIR_PLAN_2026-09-10.md` and the user-supplied repair handoff. It does not replace File A or grant production authority.

## Baseline and scope

- GitHub PR #6 is open at `6de1e14973edcf62b61c9b6a1441214ace656ec4`; base `f99e7eb3e764b3fb43aa55432abcdf78cd68191e`.
- CI run `34486533849`, backend job `102902136101`: three failures, 1671 passes; compile/frontend pass; Ruff skipped. Both R18 failures reproduced locally before edits.
- Work uses an isolated checkout. The unrelated dirty `D:/TrendForge` main checkout is preserved.
- INTENT: restore valid adversarial test inputs, supply the existing XLS parser dependency, then prove the requested immutable recovery and finalizer lifecycle.

## Milestones and acceptance

1. Repair the three CI failures: alias-aware semantic tampering plus duplicate-key rejection; governed SQL UPDATE/DELETE refusal; pre-guard corruption rejection; `xlrd==2.0.2`. Verify compile, focused tests, five 03D suites and populated EIA records.
2. Complete the handoff's remaining 03D recovery gates using existing R18/retention owners: preserve E1, append deterministic E2 and immutable reconciliation evidence; reject genuinely APPLIED old events/references; test crash/replay, simultaneous finalizers, duplicate dispatch, busy paths and split-state refusal.
3. Verify full backend, Ruff, frontend and normalized Mypy delta against 03C. Update authoritative status/evidence. Prepare the reviewed diff before requesting commit/push approval; after publication verify CI at the new exact PR head.

The user requested these local repairs in the attached handoff. Installs, publication and real database operations retain their separate consent boundaries. Only scratch databases are used here.

## Decision and constraints

No-build leaves reproducible failures. Weakening validation/immutability is rejected. The smallest complete repair updates tests/dependency and adds recovery through existing owners; a parallel registry or retention database is rejected. The weakest point is recovery under concurrent publication; deterministic crash/concurrency tests must falsify unsafe behavior before acceptance.

Preserve alias rejection, semantic hashes, immutable rows, exact PIT parents and all research ceilings. No merge, 03E/03F work, live migration, promotion, broker or execution change. Any APPLIED pre-fix semantic identity stops recovery for explicit review. Rollback is the isolated diff; no production data is touched.

## Implemented behavior

- Canonical alias-aware tamper input reaches semantic validation. Duplicate alias/name input still raises `extra_forbidden`. Normal SQL UPDATE/DELETE remains blocked. Corruption tests use isolated historical schemas before installing guards; no test removes a production trigger.
- `xlrd==2.0.2` is declared beside openpyxl. User approved an isolated test-folder install. The exact official XLS (104448 bytes, OLE signature) produces eight numeric regional records dated 2026-09-04. Masking xlrd against the same bytes reproduces `WAIT_SCHEMA_MISMATCH`; restoring it produces `PARSED_STRUCTURED`. Parser/fetcher behavior is unchanged. The CSV route also returned eight rows, but its existing date extraction returned null; this is not evidence of freshness validation.
- `r18_retention_supersessions` is additive within the existing research database/schema owner. Explicit `supersede_rhist03d_event(event_id, reviewed_by=..., reason=...)` validates the original event, exact artifact and pending link under a writer transaction. It preserves E1 and the original link, stages deterministic E2, and appends immutable reviewer/reason/hash linkage. Failure rolls back E2 and linkage together. Replay returns the same linkage.
- Reads resolve the preserved link through verified supersession evidence and use only E2 for retention/authority proof. Reads perform no recovery. Superseded E1 cannot be updated/deleted/dispatched or subsequently registered by a stale worker. Already APPLIED old semantic events/references stop for migration review. Legacy market-data ML_DATASET/AUDIT events are not classified from the enum alone.
- Finalization rechecks both local states under the writer lock. A second finalizer accepts an already completed identical pair; split states fail closed. Fault points cover before dispatch, after authority registration, after outbox acknowledgement, after parent proof, between local link/artifact writes and before commit. Each crash remains hidden/replayable.
- Typed late dispatch failures cannot downgrade APPLIED. Concurrent authority inserts use conflict handling followed by full immutable-value equality: identical values converge; different values still fail.
- Stored semantic verification now checks the requested indexed ID/version against the validated payload. Pre-guard index corruption is rejected.
- Explicit `__all__` re-export preserves the R18 API and removes the previously unreached Ruff warning.

## Evidence and traceability

| Requirement | Evidence |
| --- | --- |
| Original R18 failures | Both reproduced before edits; repaired ML suite: 28 passed. |
| Existing 03D contracts | Five suites: 54 passed after the immediate repairs. |
| Recovery/crash/concurrency | First matrix: 9 failures and 4 passes before implementation; next matrix: 72 passes across 03D. Broader checks exposed the real concurrent authority INSERT race; a forced two-reader test reproduced its UNIQUE failure before the final repair. |
| Exact indexed identity | Both wrong-ID/wrong-version tests failed before the added verifier check. |
| Registration safety | 48 focused authority/retention/recovery tests passed; final forced same-value/conflicting-value/concurrent-finalizer checks: 3 passed. |
| Mypy | Actual accepted 03C source at `2079336768907cf9f0668a8798cd631007c6e74f` and final repaired source checked in the same local environment: 512 errors each, zero new and zero removed normalized errors/notes. |
| EIA source | Exact XLS and same-byte missing-dependency experiment described above. |
| Frontend | npm test passed after documentation changes: 220/220 primary checks plus all additional suites. |
| Full backend | Final repaired source: **1699 passed, zero failed, zero skipped, one Starlette deprecation warning**, in 904.25 seconds. Earlier interrupted runs are not counted. |
| Compile / Ruff | Passed on final source. |

TWINS: found and replaced a second corruption test that dropped a guard in `test_rhist03d_artifact_retention.py`; fixed the latent R18 re-export warning. Reviewed both dispatcher status updates, pending reconciliation, R18 local state writes and indexed identity verification. Legacy identity regression anchors remain covered.

## Operational and acceptance boundary

### Accepted publication checkpoint - 2026-09-11

The user authorized publication with "COMMIT THE FIX YOU DID LOCALLY TO GITHUB".
GitHub commit `fce62874a61e4e2bb6d939bef6d0811e5a266996` has the exact tested tree
`9295187c49ee7fe5f5005d6ec42a92f94775dcf8` (the local commit's identity differs
because publication used the GitHub connector). CI `34496385997` completed /
success: 1699 backend tests, compile, Ruff and frontend passed; Mypy retains
512 legacy errors / 70 files, normalized delta 0. This is the 03D implementation
acceptance checkpoint. 03D is IMPLEMENTED + TESTED; 03E is NEXT / UNLOCKED;
03F is GATED on 03E. Full R-HIST-03, live-data and production acceptance are not
complete. The following local pre-publication record is historical, superseded
only for publication/CI/stage status by this checkpoint. No real database was
migrated. Existing operational boundaries still apply.

### Historical local pre-publication record

Apply the existing explicit R18 schema operation to a reviewed target database before recovery; it now includes the additive supersession table/guards. Stop old workers before deploying this recovery-capable code. Inventory first; do not attempt recovery if a pre-fix semantic event/reference was genuinely APPLIED. For an eligible event, invoke the explicit recovery function with a real reviewer and reason, then separately finalize using full parent verification. Never modify the original event/link identity, invent missing evidence or use a governed read to repair history.

Only scratch databases were used. Local repair and validation milestones are complete: full backend, compile, Ruff, frontend and normalized Mypy comparison passed their stated gates. No commit, push, PR metadata edit, production migration or broker action has been performed. Publication requires separate approval. After publication, record the exact new PR head and matching CI run, compare its normalized Mypy diagnostics, and only then evaluate the 03D stage gate. Local self-review verdict: VERIFIED WITH CAVEATS (post-publication exact-head CI and live/production acceptance remain unverified).

R-HIST-03D: IN PROGRESS. R-HIST-03E and 03F: LOCKED. Full R-HIST-03: NOT COMPLETE. LIVE-DATA-VERIFIED (03D): NO. PRODUCTION-ACCEPTED: NO. The narrow EIA observation does not change these states or grant PIT/model/promotion/execution authority.
