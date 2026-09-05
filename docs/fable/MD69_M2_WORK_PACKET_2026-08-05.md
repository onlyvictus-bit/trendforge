# MD69-M2 Work Packet — CAS, Manifests, Temporary Schema, Retention

Status: **COMPLETE — VERIFIED**

## Authority and intent

- Approved range: user's 2026-08-05 instruction, "approve for all".
- Selected controlling work: File A `R0` storage/source-contract boundary with
  `CROSS-012`, `TDG-GAP-018`, `FMR-001`, and `FMR-010` acceptance lineage.
- INTENT: add one local, restart-safe market-data storage layer that reuses the
  TrendForge database path, stores identical bytes once, preserves last-good
  state, writes atomic manifests, and deletes only safely eligible retained days.
- Acceptance ceiling: temporary databases and deterministic fixtures only.
  No live fetch, production migration, scheduler, service, panel change, broker,
  quantity, order, or trading authority.

## Allowed implementation surfaces

- `backend/trendforge_api/market_data_store.py`
- `backend/tests/test_market_data_store.py`
- MD69/Fable status, architecture, traceability, validation, and file-map docs

Pre-edit runtime manifest hash:
`1A4EAA1ADB95260241892105481FBC4D85B1824D01D7830AF6FC69A965F574BE`

## Observable done criteria

1. An additive schema migration succeeds only against a caller-supplied
   temporary SQLite database during M2 verification.
2. SHA-256 objects deduplicate across trading days and install atomically.
3. Failed/invalid attempts never replace the source's last-good pointer.
4. A snapshot manifest is atomically written and can contain exactly 69 unique
   source entries.
5. Five completed trading days are retained; current-day, outside-root,
   symlink/reparse, referenced-object, and dry-run safety are test-covered.
6. Focused tests, Python compilation, Ruff, and surrounding source tests pass.

## Observed result

- 13/13 focused storage tests passed.
- 47/47 combined registry, storage, source-runtime, calendar, and live-panel
  tests passed; one dependency deprecation warning remains.
- Python compilation and Ruff passed.
- Only caller-supplied temporary SQLite databases were migrated.
- No fetch, production migration, scheduler, or panel mutation occurred.
