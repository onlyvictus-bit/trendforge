# MD69 parameter-resolution repair review — 2026-08-06

## Outcome

The existing 69-source collector now resolves the five previously missing
parameter contracts without hard-coding a second source list or creating a
second downloader. Manual refresh and scheduled snapshots use the same path.

## Implemented flow

1. Run context-independent feeds with the existing bounded service.
2. Commit their normalized last-good objects.
3. Rebuild a bounded `ParameterContext` from those committed objects.
4. Run only the parameter-dependent feeds.
5. Persist each result independently; one failure cannot cancel another feed.

The saved-data provider derives sector names from `nse_all_indices`, eligible
stock option symbols and nearest expiries from `nse_fo_bhavcopy`, and a ranked
option shortlist from `nse_most_active_underlying`.

`MARKET_DATA_OPTION_SYMBOL_LIMIT` defaults to 8 and is hard-capped at 20.
The provider performs no network calls and rejects object paths outside the
collector's content-addressed object directory.

## Source contract changes

| Source | New acquisition contract |
|---|---|
| `bse_corporate_announcements` | One market-wide date-window request; blank BSE scrip filter |
| `nse_shareholding_pattern` | One market-wide `index=equities` request |
| `nse_pit_symbol` | One current market-wide PIT request; valid empty remains valid empty |
| `nse_sector_constituents` | Bounded fan-out over saved current sector index names |
| `nse_option_chain_equity` | Current `option-chain-v3`, bounded active symbols, nearest expiry |

No Consensus voter, Screener score, broker path or order behavior changed.

## Verification evidence

- Focused offline suite: `55 passed`, one unrelated Starlette warning.
- Full manual registry run: `69 attempted / 69 completed`.
- Manifest: `D:\TrendForge\data\market_data\2026-08-06\snapshots\manual-20260806-123411\manifest.json`.
- Statuses: 38 `SUCCESS_NEW`, 22 `SUCCESS_UNCHANGED`, 2 `VALID_EMPTY`,
  6 `FAILED`, 1 `PARTIAL`.
- Repaired rows: BSE announcements 1, shareholding 2,285, sectors 25,
  option-chain contracts 464, PIT 0 valid-empty.

The remaining failures/partial result are unrelated: `nse_slb`, three CFTC
routes, `amfi_scheme_wise`, `nsdl_fpi_fortnightly`, and partial
`nse_large_deals_snapshot`.

## Verdict

**VERIFIED WITH CAVEATS.** The requested parameter failures are repaired and
the full job completes with per-source isolation. This does not claim that all
69 sources are populated or that provisional schedules are officially verified.
