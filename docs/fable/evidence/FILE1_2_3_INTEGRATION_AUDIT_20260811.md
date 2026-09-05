# Files 1-3 Production Integration Audit

Date: 2026-08-11

Verdict: **VERIFIED WITH CAVEATS**. Eighteen of 24 candidate families are
covered by populated production output. Four are blocked/not implemented and
two are intentionally rejected. Therefore the claim "all links were added"
is false, while the 18 accepted mappings are present and populated.

## File 1 (`C:\Users\sakth\Downloads\1.txt`)

| Candidate family | Classification | Production mapping | Latest persisted proof |
|---|---|---|---|
| CFTC COT | ENHANCED_EXISTING | `cftc_cot` | 96 rows; data 2026-07-28 |
| NSE FII/DII | ENHANCED_EXISTING | `nse_fii_dii` | 2 rows; data 2026-08-06 |
| NSE participant OI | ENHANCED_EXISTING | `nse_participant_oi` | 4 rows; data 2026-08-06 |
| NSE FII derivatives | ENHANCED_EXISTING | `nse_fii_derivatives_stats` | 18 rows; data 2026-08-06 |
| BSE participant OI | ADDED_NEW | `bse_participant_oi` | 4 rows; data 2026-08-10 |
| BSE FII/DII | ADDED_NEW | `bse_fii_dii` | 2 rows; data 2026-08-10 |
| MSE participant OI | BLOCKED | none | No reachable verified workbook; no placeholder key |
| MCX warehouse/delivery | ENHANCED_EXISTING | `mcx_warehouse_stocks`, `mcx_delivery_reports` | 24 + 24 rows; data 2026-08-06 |

Coverage: **7/8 families**.

## File 2 (`C:\Users\sakth\Downloads\2.txt`)

| Candidate family | Classification | Production mapping | Latest persisted proof |
|---|---|---|---|
| NSDL FPI sectoral | REUSED_EXACT_OUTPUT | `nsdl_fpi_fortnightly` | 48 rows; data 2026-07-31 |
| AMFI monthly category AUM | BLOCKED | none | Verified older workbook route was never integrated |
| Real Baltic Dry Index | ADDED_NEW | `tradingeconomics_bdi` | 1 row; data 2026-08-10 |
| Yahoo dry-bulk route | ADDED_NEW | `yahoo_bdry_shipping_proxy` | 251 rows; data 2026-08-10; labelled ETF proxy |
| Google Trends route | ADDED_NEW | `google_trends_india_rss` | 10 rows; data 2026-08-10; current topics, not keyword history |
| Westmetall LME repair | BLOCKED | none | Viable third-party page was checked but repair never entered registry |

Coverage: **4/6 families**. The supplied Yahoo `^BADI` and pytrends methods are
rejected; the table counts their honest BDRY and official RSS alternatives as
family coverage and never relabels them as the failed originals.

## File 3 (`C:\Users\sakth\Downloads\3.txt`)

| Candidate family | Classification | Production mapping | Latest persisted proof |
|---|---|---|---|
| NSE FII/DII wrapper | REUSED_EXACT_OUTPUT | `nse_fii_dii` | 2 rows |
| Sector RRG/yfinance proposal | REJECTED | `nse_all_indices` retained as source data only | Proposed code omitted an executable source and was derived analytics |
| CRISIL ratings | ADDED_NEW | `crisil_ratings` | 100 rows; data 2026-08-10 |
| ICRA ratings | ADDED_NEW | `icra_ratings` | 20 rows; data 2026-08-10 |
| CARE ratings | ADDED_NEW | `care_ratings` | 1,000 rows; data 2026-08-10 |
| NewsAPI | BLOCKED | none | API key and usage approval required |
| Google News RSS | ADDED_NEW | `google_news_rss` | 4 age-gated rows; data through 2026-08-09 |
| StockEdge claimed API | REJECTED | none | No stable public data endpoint or parameters |
| NSE bulk deals | REUSED_EXACT_OUTPUT | `nse_bulk_deals_today_csv`, `nse_bulk_deal_symbol` | 139 + 50 rows |
| NSE block deals | REUSED_EXACT_OUTPUT | `nse_block_deal` | 3 rows |

Coverage: **7/10 families**.

## Cross-checks

- Registry: 112 rows / 112 unique / 112 compiled; SHA-256
  `95B67C66279C04D96C4CB16E766AC30BD0BDA51FC08E9FFD8B34BBB5B2F327C5`.
- Catalog: 154 rows / 118 logical keys; all 112 registry keys represented.
- All 18 covered file-1/2/3 families have a positive-row last-good object in
  `D:\TrendForge\data\trendforge_research.db` (read-only audit).
- Backend Pack-6/7/parser/registry/service suite: 58 passed; targeted Ruff passed.
- Inventory frontend suites: 13/13 scripts passed after repairing two obsolete
  fixture pins (old 112-card count and pre-2026-08-06 Consensus hash) and one
  PIT fixture that still expected the earlier two-row sample.
- Consensus output and Screener A-only financial golden suites passed. No
  source from files 1-3 was promoted into a new scoring formula.

Research-only data. A populated last-good object proves integration and parsing,
not publication freshness or trading suitability.
