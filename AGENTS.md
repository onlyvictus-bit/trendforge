# TrendForge Engineering Rules

## Authority

1. Read this file and File A (`docs/fable/new_merge_PLAN_2026-07-18.md`) before changing business logic. Before each milestone, also read the current `docs/BUILD_STATUS.md`, `docs/VALIDATION.md`, `docs/fable/remaining_build/README.md`, and then `docs/fable/remaining_build/REMAINING_PROJECT_BUILD_FILES.md` to locate the relevant code and tests. The remaining-project file map is a checklist/navigation aid only; it cannot change File A scope, sequence, IDs, or acceptance ceilings. Open `TREND_FORGE_ARCHITECTURE.md` for system boundaries, `TREND_FORGE_SOURCE_REGISTRY.md` for source meaning, and Hybrid detail only through File A Section 0.5/Section 25 pointers. Open `docs/fable/FINAL_MERGE_PLAN.md` for every milestone mapped to its `FMR-*` addendum, including all-stock research, discovery, PKScreener, derivatives, Gamma/GEX, strike intelligence, and trader-facing research workflows. The Final Merge plan is a mandatory product/design addendum, not a second build sequence; File A still controls scope, order, stable implementation IDs, states, ceilings, and acceptance. `present.md` is historical context, not the current build order.
2. The preserved master plan hash is recorded in `README.md` and `docs/DECISIONS.md`.
3. Later explicit final rules override earlier historical text.
4. Historical appendices and backup files are evidence, not a reason to undo current final decisions.

## Safety

- TrendForge v1 is read-only. Do not add brokerage order placement.
- Missing, stale, metadata-only, unofficial-only or conflicting evidence cannot produce `CONFIRMED`. Current research states are non-executable.
- A URL, HTTP 200 response or parser invocation is not proof that usable data exists.
- Source success requires real schema-valid parsed trading records such as
  symbols, prices, OHLCV, OI, contracts, deals, holdings or restrictions.
  Metadata-only, malformed, blocked, stale-only and unproven empty results do
  not count as usable populated data.
- When an existing TrendForge source returns no usable populated records, test
  the user-supplied prototype or pasted route as an untrusted fallback lead.
  If it produces reproducible official parsed data, integrate only its smallest
  verified transport/parser improvement into the existing archive, parser,
  storage and source-health pipeline. Do not preserve a failing implementation
  merely because it already exists, and do not create a parallel downloader,
  duplicate database or duplicate source contract.
- Do not count mirrored/correlated evidence as independent confirmation.
- Participant OI is regime context, AMFI is delayed swing context, CFTC is delayed commodity context, and SLB is a borrow proxy.
- Never hardcode credentials or include secrets in logs, fixtures, browser code or the database.

## Documentation Consolidation - 2026-07-14

The active root Markdown set is now `AGENTS.md`, `present.md`,
`TREND_FORGE_ARCHITECTURE.md`, and `TREND_FORGE_SOURCE_REGISTRY.md`.
`README.md`, `REVIEW.md`, and `TREND_FORGE_IMPLEMENTATION_PLAN.md` are embedded
verbatim in `present.md` under the `Consolidated Master Topic Index` and
`EMBEDDED SOURCE` headings. Their unchanged originals are retained under
`delete/top_level_md_consolidation_2026-07-14/`. Use
`documentation_consolidation_manifest.json` to verify hashes and byte ranges.

## Workflow

1. Add or update tests before implementation for safety-critical logic.
2. Preserve point-in-time cutoffs and exact source/parser/feature versions.
3. Use `apply_patch` for manual edits.
4. Run relevant tests, full backend tests, Python compilation and frontend checks before marking a milestone complete.
5. Update `docs/BUILD_STATUS.md` and `docs/VALIDATION.md` with commands and honest results.
6. Keep the app runnable at the end of each milestone.

## Boundaries

- Backend: `backend/trendforge_api`.
- Backend tests: `backend/tests`.
- Frontend: `frontend`.
- Local state: `data`; do not commit credentials or assume fixture state is production evidence.
- Canonical source inventory: `TREND_FORGE_SOURCE_REGISTRY.md`.
