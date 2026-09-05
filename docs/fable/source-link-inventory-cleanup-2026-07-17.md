# Source Link Inventory Cleanup - 2026-07-17

## Intent

Reduce `D:\TrendForge\data\reports` report sprawl into a reusable source-link master while preserving every link and audit detail needed for later scanner work.

## Approved Scope

User approved creation and verification of a master file, with intermediate report files archived rather than deleted.

## Outputs

- `D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx`
- `D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.csv`
- `D:\TrendForge\data\reports\archive\2026-07-17_link_report_cleanup\`

## Verification Evidence

- Current inventory rows included: 233
- Old `source_inventory_audit_*.csv` fragments scanned: 450
- Fragment evidence rows preserved in workbook: 3,680
- Report CSV rows scanned for URL coverage: 4,701
- Unique canonical links found across report CSVs: 280
- Unique canonical links in master workbook: 280
- Missing links from master workbook: 0
- Extra links in master workbook versus report evidence: 0
- `MASTER_CURRENT` rows: 296
- Fragment-only links preserved for review: 63
- Placeholder/test fragment-only links marked: 5
- Duplicate review rows preserved: 198
- Archived indexed report files: 470
- Top-level files remaining in `data/reports`: 2

## Notes

- The master workbook includes sheets for README/index, current master rows, old fetch evidence, all links found in reports, fragment-only links, duplicate review rows, and archive index.
- No report evidence was deleted. Intermediate files were moved into the dated archive folder.
- Verification inspect logs generated during the process were also moved into the archive after validation.

## Intraday Stock-Detail Source Update - 2026-07-17

### Intent

Add the intraday stock-screening API bundle from the user-provided guide without creating another source-link report file.

### Code Changes

- Added config contracts for NSE OI contract buckets, NSE live equity derivatives, corrected NSE sector constituents, BSE order-win announcements, NSDL fortnightly FPI context, and Equitymaster reference-only discovery.
- Corrected existing NSE index constituent contracts from `equity-stockIndices` to `equity-stock-indices`.
- Added `trendforge_api.intraday_stock_details` to convert OI buckets, active derivatives, sector constituents, OI-underlying totals, BSE order announcements, and NSDL HTML table presence into a research-only stock-detail snapshot.
- Added CLI command `fetch-intraday-stock-details`.
- Added offline tests for request building, URL encoding, evidence merging, and persistence.

### Verification Evidence

- `python -m py_compile` passed for changed backend modules.
- `pytest backend/tests/test_intraday_stock_details.py backend/tests/test_market_activity.py -q` passed: 11 tests.
- Live CLI verification `fetch-intraday-stock-details --from-date 2026-07-17 --to-date 2026-07-17 --limit 5 --concurrency 2` completed with 15 source fetches, 14 raw archived responses, 1 valid empty response, 0 broken responses, and a research-only snapshot.
- Live verification JSON saved under `data/reports/archive/2026-07-17_link_report_cleanup/intraday_stock_detail_live_verify_2026-07-17.json`.
- Master workbook was rebuilt from archived report CSVs plus current `config/config.yaml` endpoint contracts.
- Unique canonical links in master workbook: 332.
- Missing links from rebuilt master workbook: 0.
- Extra links in rebuilt master workbook: 0.
- Top-level report files remain limited to `SOURCE_LINK_INVENTORY_MASTER.xlsx` and `SOURCE_LINK_INVENTORY_MASTER.csv`.

### Screener Deep-Dive Update - 2026-07-17

- Integrated useful logic from the user-provided NSE screener module into TrendForge instead of copying it directly.
- Added optional symbol deep-dive requests for `nse_quote_equity`, `nse_quote_equity_trade_info`, `nse_option_chain_equity`, and `nse_quote_derivative`.
- Added normalized candidate fields for LTP, VWAP, quote change, delivery percentage, PCR, max pain, support, resistance, ATM IV, derivative contract count, and derivative quote OI.
- Added parameterized NSE quote-page referer support in the endpoint client and config.
- Offline tests passed again: `pytest backend/tests/test_intraday_stock_details.py backend/tests/test_market_activity.py -q` = 11 passed.
- Live RELIANCE deep verification completed as research-only with 19 source requests. Broad OI/derivatives/sector/BSE sources archived, but `quote-equity` and `trade_info` returned NSE 403 and `quote-derivative?symbol=RELIANCE` returned NSE 404 from this machine. Direct `curl` check also returned 403 for `quote-equity`, so these remain fail-closed rather than treated as empty data.
- Master workbook was rebuilt again including config referer and seed URLs.
- Unique canonical links in master workbook after referer update: 347.
- Missing links from rebuilt master workbook: 0.
- Extra links in rebuilt master workbook: 0.

### Caveats

- New intraday stock-detail output is research-only and cannot unlock READY by itself.
- Equitymaster remains reference/discovery only because the guide says there is no public API and the page may block bots or require login for complete data.
- NSDL fortnightly FPI is sector-level context, not stock-level FII buying proof.

## Working-Only NSE Screener Update - 2026-07-17

### Intent

Integrate only the NSE/BSE links the user verified as live-working for stock screening and keep failed endpoints out of the active screener fetch path.

### Activated In Screener Fetch Path

- `nse_oi_spurts_contracts`: four nested OI buckets flattened into `LONG_BUILDUP`, `SHORT_BUILDUP`, `SHORT_COVERING`, `LONG_UNWINDING`.
- `nse_oi_spurts`: underlying-level OI/value activity.
- `nse_live_equity_derivatives_stock_opt`: active stock options.
- `nse_live_equity_derivatives_stock_fut`: active stock futures.
- `nse_preopen_fo`: F&O pre-open gap and IEP context.
- `nse_all_indices`: market and sector regime.
- `nse_sector_constituents`: corrected `equity-stock-indices` endpoint.
- `nse_block_deal`: live block-deal endpoint, with valid-empty handling.
- `bse_order_win_announcements`: BSE order-win catalyst announcements.
- `nsdl_fpi_fortnightly`: sector-level FPI context only.

### Explicitly Disabled From This Screener Path

- `nse_quote_equity`
- `nse_quote_equity_trade_info`
- `nse_option_chain_equity`
- `nse_quote_derivative`
- historical NSE bulk-deal endpoints from the pasted module

Reason: user-provided live verification showed 403/404/503/empty or unstable behavior for these methods. They remain registered contracts for future investigation, but are not fetched by `fetch-intraday-stock-details`.

### Verification Evidence

- `python -m py_compile D:\TrendForge\backend\trendforge_api\institutional_sources.py D:\TrendForge\backend\trendforge_api\intraday_stock_details.py D:\TrendForge\backend\trendforge_api\cli.py` passed.
- `pytest D:\TrendForge\backend\tests\test_intraday_stock_details.py D:\TrendForge\backend\tests\test_market_activity.py -q` passed: 11 tests.
- Live CLI verification `fetch-intraday-stock-details --from-date 2026-07-17 --to-date 2026-07-17 --limit 5 --concurrency 2` completed with 0 broken responses.
- Live verification JSON saved under `data/reports/archive/2026-07-17_link_report_cleanup/intraday_stock_detail_working_sources_verify_2026-07-17.json`.

## Linked / Not-Linked Sheet Reconciliation - 2026-07-17

### Intent

Make `SOURCE_LINK_INVENTORY_MASTER.xlsx` the current single source of truth for link status after the working-only screener update.

### Changes

- Rebuilt the master workbook from archived report CSVs plus current `config/config.yaml` endpoint contracts.
- Updated the workbook builder so recently verified working research screener endpoints are classified as `LINKED_USABLE_FOR_SCREENER`.
- Preserved endpoint-specific keys alongside normalized source keys so stock option/future endpoints do not collapse into ambiguous derivative rows.
- Removed rows from `NOT_LINKED_SOURCES` when the same canonical URL or active source key is already present in `LINKED_SOURCES`.
- Added `SUPPRESSED_NOT_LINKED_DUPES` inside the workbook to preserve those removed not-linked duplicate rows without cluttering the active not-linked queue.

### Verification Evidence

- Master workbook unique link coverage: 347 links in report/config evidence, 347 links in workbook, 0 missing, 0 extra.
- `LINKED_SOURCES`: 86 rows.
- `NOT_LINKED_SOURCES`: 244 rows.
- `SUPPRESSED_NOT_LINKED_DUPES`: 17 rows.
- URL overlap between `LINKED_SOURCES` and `NOT_LINKED_SOURCES`: 0.
- Active source-key overlap between `LINKED_SOURCES` and `NOT_LINKED_SOURCES`: 0.
- Formula/error scan: 0 formula error matches.
- Render check completed for bounded top ranges of all workbook sheets.
- Top-level `data/reports` remains limited to `SOURCE_LINK_INVENTORY_MASTER.xlsx`, `SOURCE_LINK_INVENTORY_MASTER.csv`, and `archive/`.

## NSE 11-Source Deep Scanner Merge - 2026-07-17

### Intent

Merge the useful parts of the user-provided `nse_client.py` and `scanner.py` guide into TrendForge's existing source-gated screener path without duplicating standalone code or weakening fail-closed behavior.

### Implemented

- Added market-level NSE contracts to the intraday stock-detail request plan:
  - `nse_most_active_underlying`
  - `nse_market_turnover`
  - `nse_variations_gainers`
  - `nse_variations_loosers`
  - `nse_financial_results`
- Added symbol-level deep-dive requests when a symbol is supplied:
  - `nse_quote_equity`
  - `nse_quote_equity_trade_info`
  - `nse_option_chain_equity`
  - `nse_quote_derivative`
  - `nse_pit_symbol`
- Updated NSE variation URLs to use `index=gainers` and `index=loosers`, matching the verified NSE spelling and payload shape.
- Updated `nse_pit_symbol` and `nse_financial_results` to use bounded NSE `DD-MM-YYYY` dates instead of broad unbounded pulls.
- Added normalized candidate fields for futures basis, futures OI change, most-active derivative value, insider buy/sell/net value, insider disclosure count, recent financial result, and market context.
- Added market breadth penalty logic: weak cash breadth reduces score instead of pretending the symbol is independent of regime.

### Live Verification

- Fixed live CLI report: `data/reports/archive/2026-07-17_link_report_cleanup/intraday_stock_detail_deep_sources_verify_fixed_2026-07-17.json`.
- Live source requests in that run: 27.
- Raw archived responses: 19.
- Valid empty responses: 5.
- Broken responses: 3.
- Candidate rows: 5.
- Market context extracted:
  - cash gainers: 20
  - cash losers: 20
  - F&O gainers: 20
  - F&O losers: 20
  - market turnover records: 13
  - most-active underlying records: 215
  - financial result records for the selected date: 0
- RELIANCE received most-active derivative evidence and OI/sector/pre-open context, but quote/trade-info/derivative quote remained blocked or unavailable.

### Fail-Closed Items From The 11-Source Guide

- `nse_quote_equity`: NSE returned 403 from this machine/session.
- `nse_quote_equity_trade_info`: NSE returned 403 from this machine/session.
- `nse_quote_derivative`: NSE returned 404 for RELIANCE.
- `nse_option_chain_equity`: integrated but valid-empty in the live run.
- `nse_pit_symbol`: integrated but valid-empty for RELIANCE/date window in the live run.
- `nse_pit_annual`: still registered as a contract, but not added to the default intraday CLI path to avoid extra broad symbol-year traffic.

### Verification Evidence

- `python -m py_compile D:\TrendForge\backend\trendforge_api\institutional_sources.py D:\TrendForge\backend\trendforge_api\intraday_stock_details.py D:\TrendForge\backend\trendforge_api\cli.py` passed.
- `pytest D:\TrendForge\backend\tests\test_intraday_stock_details.py D:\TrendForge\backend\tests\test_market_activity.py -q` passed: 11 tests.
- Master workbook was rebuilt after this update.
- Rebuilt workbook counts:
  - `MASTER_CURRENT`: 363 rows
  - `LINKED_SOURCES`: 94 rows
  - `NOT_LINKED_SOURCES`: 230 rows
  - `SUPPRESSED_NOT_LINKED_DUPES`: 23 rows
  - `ALL_LINKS_FROM_REPORTS`: 347 rows
- Workbook coverage verification: 347 links in report/config evidence, 347 links in workbook, 0 missing, 0 extra.
- Linked/not-linked overlap check: 0 canonical URL overlap and 0 active source-key overlap.
- Large inspection NDJSON moved to `data/reports/archive/2026-07-17_link_report_cleanup/SOURCE_LINK_INVENTORY_MASTER_2026-07-17_after_nse_11_update.inspect.ndjson`.

## 9-Source Market Data Fetcher Merge - 2026-07-17

### Intent

Evaluate the user-provided 9-source `sources.py` guide and merge only the parts that can improve TrendForge's screener or source archive without duplicating existing code or treating raw/blocked pages as structured evidence.

### Implemented

- Added `nse_bulk_deals_today_csv` as a working NSE daily bulk-deal CSV source:
  - URL: `https://archives.nseindia.com/content/equities/bulk.csv`
  - Live check: `RAW_ARCHIVED`, 103 CSV rows.
  - Screener use: parsed into symbol-level bulk-deal notional, named client, side, quantity, and weighted average price.
- Added `bulkDealNotional` and `nseBulkDeals` to intraday stock-detail output.
- Updated MCX option-chain and market-watch contracts to the `backpage.aspx` POST shape from the guide:
  - `mcx_option_chain`: `POST /backpage.aspx/GetOptionChain`
  - `mcx_market_watch`: `POST /backpage.aspx/GetMarketWatch`
  - ASP.NET `{"d": "..."}` JSON decoding added to the shared endpoint client.
- Added `mcx_delivery_reports` endpoint contract:
  - URL: `https://www.mcxindia.com/market-operations/clearing-settlement/delivery-reports`
  - Live check: page archived as HTML.
  - Structured use remains pending until Excel link discovery/parser is implemented.
- Fixed generic seed handling so non-NSE seed-page 403 responses warn and still attempt the actual data endpoint.
- Added `archives.nseindia.com` and `nsearchives.nseindia.com` to the approved endpoint host allowlist.
- Updated the source monitor descriptor for `mcx_delivery_reports` to the current URL and parser-pending status.

### Not Copied From The Pasted Module

- `bse_insider_trading()` was not replaced with `InsiderTrading_new/w` because live verification from this machine returned HTML, while the existing `InsiderTrade15/w` route returned valid JSON.
- `nse_bulk_deals()` historical API was not added to the active screener path because live verification returned NSE 503. The working daily CSV fallback was used instead.
- AMFI NAV and BSE scrip header were already registered and tested in TrendForge, so no duplicate fetcher was created.

### Live Verification

- NSE daily bulk CSV:
  - state: `RAW_ARCHIVED`
  - records: 103
  - URL: `https://archives.nseindia.com/content/equities/bulk.csv`
- MCX market watch:
  - state: `WRONG_CONTENT`
  - result: endpoint returned HTML instead of JSON from this environment.
- MCX option chain:
  - state: `WRONG_CONTENT`
  - result: endpoint returned HTML instead of JSON from this environment.
- MCX delivery reports:
  - state: `RAW_ARCHIVED`
  - records: 1 HTML page
  - structured parser: pending.
- Intraday screener live report:
  - path: `data/reports/archive/2026-07-17_link_report_cleanup/intraday_stock_detail_after_9_source_fetchers_2026-07-17.json`
  - source requests: 28
  - raw archived: 20
  - valid empty: 5
  - broken: 3
  - candidates: 5
  - new NSE bulk CSV source archived with 103 rows.

### Test Evidence

- `python -m py_compile` passed for:
  - `institutional_config.py`
  - `institutional_sources.py`
  - `intraday_stock_details.py`
  - `commodity_context.py`
  - `cli.py`
- Regression tests passed:
  - `test_intraday_stock_details.py`
  - `test_market_activity.py`
  - `test_extended_market_sources.py`
  - `test_commodity_context.py`
  - `test_corporate_disclosure_fetch.py`
  - result: 30 passed.

### Master Workbook Evidence

- Master workbook rebuilt after this update.
- `MASTER_CURRENT`: 364 rows.
- `LINKED_SOURCES`: 94 rows.
- `NOT_LINKED_SOURCES`: 231 rows.
- `SUPPRESSED_NOT_LINKED_DUPES`: 23 rows.
- `ALL_LINKS_FROM_REPORTS`: 348 rows.
- Workbook coverage verification: 348 links in report/config evidence, 348 links in workbook, 0 missing, 0 extra.
- Linked/not-linked overlap check: 0 canonical URL overlap and 0 active source-key overlap.
- Large inspection NDJSON moved to `data/reports/archive/2026-07-17_link_report_cleanup/SOURCE_LINK_INVENTORY_MASTER_2026-07-17_after_9_source_fetchers.inspect.ndjson`.

## NSE Index Derivative Route Merge From Pasted Module - 2026-07-17

### Intent

Evaluate the pasted `nse_client.py` guide and merge only working routes into the existing TrendForge screener code without creating duplicate standalone downloader files.

### Live Endpoint Check

- Existing `index=index_opt` returned HTTP 500.
- Existing `index=index_fut` returned HTTP 500.
- Pasted replacement `index=nse50_opt` returned JSON with 1464 rows.
- Pasted replacement `index=nse50_fut` returned JSON with 3 rows.
- Discovered Bank Nifty replacement `index=nifty_bank_opt` returned JSON with 993 rows.
- Discovered Bank Nifty replacement `index=nifty_bank_fut` returned JSON with 3 rows.
- Pasted `option-chain-indices` route returned HTTP 404 from this machine, so it was not added.
- Pasted `quote-slb` route returned HTTP 403 and existing `/api/slbs` returned HTTP 404, so no SLB replacement was accepted.

### Implemented

- Updated existing endpoint contracts:
  - `nse_live_equity_derivatives_index_opt` now uses `https://www.nseindia.com/api/liveEquity-derivatives?index=nse50_opt`.
  - `nse_live_equity_derivatives_index_fut` now uses `https://www.nseindia.com/api/liveEquity-derivatives?index=nse50_fut`.
- Added new endpoint contracts:
  - `nse_live_equity_derivatives_banknifty_opt`
  - `nse_live_equity_derivatives_banknifty_fut`
- Added these four routes to the intraday stock-detail fetch set.
- Added market-context normalization:
  - `niftyIndexOptionRecordCount`
  - `niftyIndexOptionVolume`
  - `niftyIndexOptionOpenInterest`
  - `niftyIndexFutureRecordCount`
  - `niftyIndexFutureVolume`
  - `niftyIndexFutureOpenInterest`
  - `bankNiftyIndexOptionRecordCount`
  - `bankNiftyIndexOptionVolume`
  - `bankNiftyIndexOptionOpenInterest`
  - `bankNiftyIndexFutureRecordCount`
  - `bankNiftyIndexFutureVolume`
  - `bankNiftyIndexFutureOpenInterest`
- Updated the master-workbook builder so the accepted routes are classified as linked screener sources.

### TrendForge Live Verification

- Live TrendForge `AsyncEndpointClient` fetch results:
  - `nse_live_equity_derivatives_index_opt`: `RAW_ARCHIVED`, 1464 rows.
  - `nse_live_equity_derivatives_index_fut`: `RAW_ARCHIVED`, 3 rows.
  - `nse_live_equity_derivatives_banknifty_opt`: `RAW_ARCHIVED`, 993 rows.
  - `nse_live_equity_derivatives_banknifty_fut`: `RAW_ARCHIVED`, 3 rows.
- Report saved to `data/reports/archive/2026-07-17_link_report_cleanup/index_derivative_fetch_after_pasted_module_2026-07-17.json`.

### Test Evidence

- `python -m py_compile D:\TrendForge\backend\trendforge_api\institutional_sources.py D:\TrendForge\backend\trendforge_api\intraday_stock_details.py` passed.
- `pytest D:\TrendForge\backend\tests\test_intraday_stock_details.py D:\TrendForge\backend\tests\test_institutional_screener.py -q` passed: 21 tests.

### Master Workbook Evidence

- Master workbook rebuilt after this update.
- `MASTER_CURRENT`: 366 rows.
- `LINKED_SOURCES`: 98 rows.
- `NOT_LINKED_SOURCES`: 231 rows.
- `SUPPRESSED_NOT_LINKED_DUPES`: 21 rows.
- `ALL_LINKS_FROM_REPORTS`: 350 rows.
- Workbook coverage verification: 350 links in report/config evidence, 350 links in workbook, 0 missing, 0 extra.
- Linked/not-linked overlap check: 0 canonical URL overlap and 0 active source-key overlap.
- Large inspection NDJSON moved to `data/reports/archive/2026-07-17_link_report_cleanup/SOURCE_LINK_INVENTORY_MASTER_2026-07-17_after_index_derivative_routes.inspect.ndjson`.

## Successful 12-Route Screener Source Merge - 2026-07-17

### Intent

Merge the user-listed 12 successful data routes into the existing TrendForge source catalog and screener paths without creating duplicate downloader files.

### Implemented

- Already connected and reverified:
  - `bse_sast`
  - `nse_live_equity_derivatives_index_opt`
  - `nse_live_equity_derivatives_index_fut`
  - `nse_live_equity_derivatives_banknifty_opt`
  - `nse_live_equity_derivatives_banknifty_fut`
  - `nse_most_active_volume`
  - `nse_volume_gainers`
- Newly wired into the existing source contracts and screener context:
  - `nsdl_fpi_daily_reportdetail`
  - `nse_shareholding_pattern` inside the intraday symbol request path
  - `cftc_legacy_futures_only`
  - `cftc_disagg_futures_only`
  - `cftc_tff_futures_only`
- CFTC SODA routes were bounded to `500` latest-first rows because the original `5000`-row query exceeded the 10 MB raw-response guard.

### Live Verification

- Report: `data/reports/archive/2026-07-17_link_report_cleanup/successful_12_source_fetch_after_screener_merge_2026-07-17.json`
- Route count: 12.
- Fresh `RAW_ARCHIVED`: 12.
- Broken: 0.
- Stale fallback: 0.
- Wrong content: 0.

Observed rows/tables:

```text
nsdl_fpi_daily_reportdetail                 17 HTML tables
bse_sast                                    37 rows
cftc_legacy_futures_only                   500 rows
cftc_disagg_futures_only                   500 rows
cftc_tff_futures_only                      500 rows
nse_shareholding_pattern                    91 rows for RELIANCE
nse_live_equity_derivatives_index_opt     1464 rows
nse_live_equity_derivatives_index_fut        3 rows
nse_live_equity_derivatives_banknifty_opt  993 rows
nse_live_equity_derivatives_banknifty_fut    3 rows
nse_most_active_volume                      20 rows
nse_volume_gainers                          25 rows
```

Screener snapshot check:

- Report: `data/reports/archive/2026-07-17_link_report_cleanup/successful_12_screener_snapshot_check_2026-07-17.json`
- Snapshot state: `RESEARCH_ONLY`.
- Sources in snapshot: 12.
- Fresh sources: 12.
- `nsdlFpiTableCount`: 17.
- RELIANCE candidate now carries `promoter_holding_pct=50.48`, `public_holding_pct=49.52`, `shareholding_date=30-JUN-2026`, and reason `NSE_SHAREHOLDING_PATTERN_AVAILABLE`.

### Test Evidence

- `python -m py_compile` passed for:
  - `institutional_config.py`
  - `institutional_sources.py`
  - `intraday_stock_details.py`
  - `macro_event_context.py`
- Focused regression tests passed:
  - `test_intraday_stock_details.py`
  - `test_macro_event_sources.py`
  - `test_institutional_screener.py`
  - result: 27 passed.

### Master Workbook Evidence

- Master workbook rebuilt after this update.
- Workbook path: `data/reports/SOURCE_LINK_INVENTORY_MASTER.xlsx`
- `MASTER_CURRENT`: 370 rows.
- `LINKED_SOURCES`: 105 rows.
- `NOT_LINKED_SOURCES`: 231 rows.
- `SUPPRESSED_NOT_LINKED_DUPES`: 18 rows.
- `ALL_LINKS_FROM_REPORTS`: 354 rows.
- Workbook coverage verification: 354 links in report/config evidence, 354 links in workbook, 0 missing, 0 extra.
- Linked/not-linked overlap check: 0 canonical URL overlap and 0 source-key overlap.
- Large inspection NDJSON moved to `data/reports/archive/2026-07-17_link_report_cleanup/SOURCE_LINK_INVENTORY_MASTER_2026-07-17_after_successful_12_sources.inspect.ndjson`.
