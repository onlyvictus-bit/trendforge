# MD69 Remaining Source Repairs - 2026-08-06

**Verdict:** VERIFIED WITH RESEARCH-SOURCE CAVEATS.

## Scope

Repaired the seven remaining manual/scheduled collector failures without adding
a second downloader, database, score term, consensus voter, broker path or order
path.

## Implemented repairs

| Source | Repair |
|---|---|
| `nse_slb` | Registry profile now uses the existing resolver and official dated NSE SLB open-position archive instead of the dead `/api/slbs` route. |
| `cftc_legacy_futures_only` | Added explicit Legacy commercial/non-commercial layout parsing without relabelling non-commercial positions as managed money. |
| `cftc_tff_futures_only` | Added explicit TFF dealer, asset-manager and leveraged-money parsing with financial-regime scope. |
| `cftc_cot` | Existing endpoint bundle now parses Legacy, Disaggregated and TFF responses independently and preserves `sourceLayout`. |
| `nse_large_deals_snapshot` | Structured normalization now chooses the parser named by `parser_or_adapter_id`; normalized aliases no longer select the wrong parser. |
| `amfi_scheme_wise` | Resolver seeds from the official directory page, uses bounded transient retries, and retains existing complete/partial validation behavior. |
| `nsdl_fpi_fortnightly` | Resolver discovers the newest populated static NSDL report, skips empty table pages, and parser derives the report date from the report URL while using the real sector column instead of its serial number. |

## Observed verification

The final seven-contract canary ran through `MarketDataService` with the MD69
store disabled. The existing endpoint client still archived the raw endpoint
payloads as designed; no MD69 manifest or latest-pointer database write was
requested by the canary.

| Source | Status | Data date | Parsed source rows |
|---|---|---:|---:|
| `nse_slb` | `SUCCESS_NEW / PARSED_STRUCTURED` | 2026-08-06 | 277 |
| `cftc_legacy_futures_only` | `SUCCESS_NEW / PARSED_STRUCTURED` | 2026-07-28 | 12 |
| `cftc_tff_futures_only` | `SUCCESS_NEW / PARSED_STRUCTURED` | 2026-07-28 | 9 |
| `cftc_cot` | `SUCCESS_NEW / PARSED_STRUCTURED` | 2026-07-28 | 32 |
| `nse_large_deals_snapshot` | `SUCCESS_NEW / PARSED_STRUCTURED` | 2026-08-05 | 357 |
| `amfi_scheme_wise` | `SUCCESS_NEW / PARSED_STRUCTURED` | 2026-06-30 | 440 |
| `nsdl_fpi_fortnightly` | `SUCCESS_NEW / PARSED_STRUCTURED` | 2026-07-31 | 48 |

NSDL's first parsed sector was `Automobile and Auto Components`, proving that
the serial-number bug is corrected. AMFI resolved the current published quarter
through 57 fund-directory entries and emitted the available 440 validated rows.

## Commands and results

```text
focused repair and broader source regression: 66 passed, 61 deselected
Ruff changed-file check: All checks passed
Python compileall: PASS
read-only seven-contract service canary: 7/7 SUCCESS_NEW and PARSED_STRUCTURED
```

The first two attempted broader test runs hit the existing Windows temporary
folder ACL error. The same tests passed after `--basetemp` was moved to the
writable inventory-app workspace.

## Caveats

- CFTC remains delayed weekly research context. Legacy, Disaggregated and TFF
  are different signal families and cannot be counted as three independent
  intraday confirmations.
- The CFTC endpoint contracts remain `UNVERIFIED_RESEARCH`; their transport
  warning text is retained even when structured parsing succeeds.
- AMFI and NSDL are delayed publication sources. They do not become live stock
  prices or consensus voters.
- A new persisted all-69 manual refresh was not started by this repair canary.
  The next manual or scheduled run will use these repaired contracts.

