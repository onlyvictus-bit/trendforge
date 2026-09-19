# R-HIST-03D PR #6 Full-Run Lint Repair Addendum — 2026-09-10

## Why this addendum exists

The functional PR #6 repair was documented in `R-HIST-03D_PR6_FAILURE_REPAIR_AND_VALIDATION_RECORD_2026-09-10.md` and then exercised by a full GitHub CI run at head `430fa0299f06c3448534836c17809db2f7550550`.

That full run exposed a second quality gate that the earlier failing backend suite had never reached: Ruff linting of existing 03D R18 façade/governance files.

## Full-run evidence at `430fa029...`

GitHub Actions run: `34480504861`.

Observed results:

- backend tests: **1,662 passed, 0 failed, 2 warnings** in 241.58 seconds;
- frontend: **success**;
- Mypy: **512 errors in 70 files**, returning to the accepted 03C legacy count/file baseline and removing the new `r18_history.py` `var-annotated` diagnostic;
- Ruff: **failed with 73 lint findings**.

The Node 20 deprecation messages were informational; Actions ran on Node 24 and they were not the failure cause.

## Ruff root cause

The Ruff failures were concentrated in:

- `backend/trendforge_api/selection/r18_governance.py`
- `backend/trendforge_api/selection/r18_store.py`

They consisted of:

1. `F401` unused-import findings for symbols intentionally imported as public façade/re-export API;
2. `E701` multiple statements after a colon on one line;
3. `E702` semicolon-separated multiple statements on one line.

These were latent 03D code-quality issues. They were not created by the canonical-hash or retention-identity repair; earlier runs did not reach Ruff because backend tests failed first.

## Safe repair law

The lint repair must not remove public 03D façade symbols just because Ruff sees them as unused internally. Existing tests and callers access those names through the façade modules.

Therefore:

- preserve the imported public symbols;
- declare the intended façade exports explicitly with `__all__`;
- expand compressed one-line statements into normal structured Python;
- move local `hashlib`/`json` imports to module scope where applicable;
- preserve SQL schema, hashes, governance behavior, return values, and authority ceilings;
- make no promotion, strategy, broker, or execution-authority change.

## GitHub lint-repair commits

1. `de28347c99aa91ac2106b22cb4a5bc15f6bc1fd7`
   - `r18_governance.py`
   - adds explicit public `__all__` for the R-HIST-03D façade imports;
   - expands E701/E702 one-line statements and long constructions without changing logic.

2. `81f60650ff08b956b3dc9cdeac9e1866d90f208a`
   - `r18_store.py`
   - adds explicit public `__all__` for history/finalization façade imports;
   - normalizes imports and expands compressed schema/persistence/read code without changing behavior.

## Acceptance after this addendum

The next authoritative CI must be associated with the PR #6 head containing:

- the original hash/retention/test repair;
- both lint-repair commits;
- this documentation addendum.

Required evidence remains:

```text
backend tests: 0 failures
Ruff: pass
frontend: pass
Mypy: no new normalized diagnostics versus accepted 03C baseline
PR exact head: verified
```

A successful CI repair does **not** by itself mark the complete 03D production-hardening contract accepted. Strict semantic canonicalization, old-event inventory/supersession, DB immutability guards, crash/concurrency testing, dispatch error taxonomy, and stronger upstream/downstream PIT-parent proof remain separate 03D gates documented in the main repair record.

Do not advance to 03E merely because this CI regression set becomes green.

LIVE-DATA-VERIFIED: NO.

PRODUCTION-ACCEPTED: NO.

PIT/model/strategy/execution authority: unchanged.
