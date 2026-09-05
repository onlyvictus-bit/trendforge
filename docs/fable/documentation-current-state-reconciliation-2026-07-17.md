# Documentation Current-State Reconciliation - 2026-07-17

## Intent

Bring current source-link and screener documentation into agreement with the
verified July 17 twelve-route merge while retaining every earlier dated result
as historical evidence.

## Scope

- Update the current authority at the top of `TREND_FORGE_SOURCE_REGISTRY.md`.
- Update executable architecture, build status, decisions, validation and
  dependency records.
- Do not alter checksum-protected historical appendices, the archived plan,
  the consolidation manifest, frontend code or execution boundaries.

## Evidence

- Twelve live routes fetched fresh through `AsyncEndpointClient`; no broken,
  stale-fallback or wrong-content result occurred in that run.
- Focused regression suite: `27 passed`.
- Serial master-workbook reconciliation: 354 normalized links in reports and
  workbook, 0 missing and 0 extra.

## Decision

The current partition is `105` linked, `231` not linked and `18` suppressed
duplicates, which equals `354` normalized report links. `MASTER_CURRENT=370`
is a worksheet-record count and must not be substituted for the active
source-link partition. All new evidence remains research-only until the
existing parser, freshness and gate requirements are satisfied.

## Verification Required

- Confirm each current document names the twelve-route merge or its correct
  scope.
- Confirm no document promotes delayed/context data to READY.
- Confirm the source registry makes the older 233-row snapshot historical.

## Verification Result

- The registry now labels the 2026-07-15, 233-row `current_usability` table as
  a historical snapshot and gives the 2026-07-17 354-link partition precedence.
- Focused source/screener regression suite passed: `27 passed in 6.58s`.
- Python compilation passed for `institutional_config.py`,
  `institutional_sources.py`, `intraday_stock_details.py`, and
  `macro_event_context.py`.
