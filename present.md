# TrendForge Present Build Specification

Date: 2026-07-10  
Status: GUARDED_RESEARCH_BUILD_VERIFIED_LIVE_EXECUTION_BLOCKED  
Purpose: Current source of truth for what TrendForge is, what is actually built, what is unsafe, and what must be built next.

This file does not replace the historical master plan, dashboard plan, MCX plan, or audit archive. It is the short current-state contract that future developers and AI agents must read before changing the project.

## Authoritative Document Set

Future implementation must use only these four root documents as active guidance:

1. `AGENTS.md` - automatically discovered engineering, safety, documentation, and verification rules.
2. `present.md` - product intent, trading rules, current status, risk defaults, audit truth, authorization boundary, and the [current Build Order](#current-build-order).
3. `TREND_FORGE_ARCHITECTURE.md` - system design, modules, data contracts, storage, APIs, and OpenAlgo boundary.
4. `TREND_FORGE_SOURCE_REGISTRY.md` - source hierarchy, parser scope, freshness, reference sources, and complete saved-link inventory.

The former standalone `TREND_FORGE_IMPLEMENTATION_PLAN.md` is not an active root file. Its complete milestones, tests, failure cases, acceptance criteria, and release gates remain available as the [embedded historical implementation plan](#embedded-source-implementation-plan) in this document. The unchanged original is retained at `delete/top_level_md_consolidation_2026-07-14/TREND_FORGE_IMPLEMENTATION_PLAN.md`, and `documentation_consolidation_manifest.json` records its source, embedded, and archive hashes.

## Current Canonical Enhancement Plan

The current source-to-screener, decision-guidance, risk, trader-interface, and OpenAlgo promotion plan is maintained in one canonical file:

`D:\TrendForge\docs\fable\TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md`

It combines the efficient `cheap filters -> candidate-only enrichment -> deterministic risk` pipeline with TrendForge's source-authority, point-in-time, independence, conflict, G00-G14, fail-closed, strategy-profile, Evidence Inspector, and OpenAlgo safety requirements. This pointer does not duplicate the plan. The plan cannot override `present.md`, `AGENTS.md`, `TREND_FORGE_ARCHITECTURE.md`, or `TREND_FORGE_SOURCE_REGISTRY.md` safety and authority rules.

There are exactly four active `.md` files under `D:\TrendForge`. Former Markdown documents are embedded verbatim in historical appendices or retained as checksum-verifiable archive evidence. Original filenames appearing inside embedded or archived historical payloads are provenance labels, not active root paths. Historical evidence cannot override the current sections of the four active documents. A historical requirement believed to be missing must first be reconciled into the current sections before runtime code changes.

## Current Source Count - 2026-07-15

The current machine-readable source inventory is:

```text
D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-14.csv
```

The filename is retained for compatibility, but the file now contains `233`
source rows after explicit user-requested additions.

Current reconciled counts:

| Classification | Count |
| --- | ---: |
| Fresh structured usable | 45 |
| Connected stale structured | 2 |
| Connected valid empty | 10 |
| Connected metadata/raw/schema-pending | 42 |
| Fetch blocked / resolver or output missing | 20 |
| Reference, secondary, duplicate, document, local or metadata-only | 114 |
| Total inventory rows | 233 |

Fresh structured remains `45`. The latest macro/agri/weather/China/MCX
operational/regulatory batch added raw and schema-pending context, not new
READY-grade source truth.

Latest 20-source macro batch result:

```text
POST /api/institutional/macro-event-sources/fetch
GET  /api/institutional/macro-event-context/latest

state: WAIT_PARTIAL_SOURCE
source completeness: 0.65
connected/archived: 13 of 20
fail-closed: 7 of 20
canUnlockReady: false
```

Connected/archived sources:

```text
usda_wasde
dgcis_trade_data
imd_rainfall_timeseries
fbil_usdinr_reference
bse_xbrl_announcements
nse_pit_annual
nse_shareholding_pattern
mca_company_master_data
cdsl_fpi_fortnightly
rbi_fpi_caution
msei_fii_dii
cftc_release_schedule
eia_petroleum_schedule
```

Fail-closed sources:

```text
des_crop_estimates: TLS verification failed locally
shfe_weekly_stock: tested dated path returned 404
china_nbs_indicator: endpoint returned 403
mcx_future_prices: MCX seed returned 403
mcx_trading_holidays: MCX seed returned 403
mcx_circulars: MCX seed returned 403
nse_xbrl_taxonomy: tested page returned 404
```

## 1. Confirmed Product Intent

TrendForge is a single-user, localhost-first stock and commodity screening system.

It must:

- scan both intraday and swing opportunities;
- cover NSE stocks and MCX commodities;
- evaluate whether entering a trade is justified;
- identify why a setup may fail before entry;
- calculate position quantity for an account of INR 1,00,000;
- send structured, time-limited trade output to the user's existing OpenAlgo-based trading bot;
- show confirmed and waiting candidates with their timeframes;
- automatically save confirmed, waiting, rejected, and watch candidates for later research and ML labelling;
- keep stale data visible with its source timestamp and stale warning;
- use free or unofficial data only as research-only fallback when an official free source is unavailable;
- never create executable READY from mock, stale, metadata-only, unofficial-only, incomplete, or scope-incompatible evidence.

No external alert integration is required in the current phase.

## 2. Non-Negotiable Risk Rule

Confidence does not directly decide quantity.

Position size must first be capped by deterministic risk:

```text
risk_per_unit = absolute(entry - protective_stop) + expected_slippage + fees
base_quantity = permitted_rupee_risk / risk_per_unit
final_quantity = minimum(
    base_quantity,
    liquidity_cap,
    margin_cap,
    correlation_cap,
    exchange_lot_cap,
    confidence_reduction_cap
)
```

Confidence may reduce quantity. Confidence must never increase quantity above the deterministic risk cap.

Low confidence must produce WAIT or a smaller pre-planned probe. It must not produce unplanned averaging down. Multi-tranche entry is allowed only when all tranche prices, total combined risk, invalidation, and maximum quantity are defined before the first order.

## 3. Preferred Account Risk Defaults

These defaults apply until the user explicitly changes them in settings:

| Control | Default |
| --- | ---: |
| Account size | INR 1,00,000 |
| Normal maximum risk per trade | 0.50% = INR 500 |
| Exceptional maximum risk | 0.75% = INR 750, only with every hard gate passing |
| Reduced-risk setup | 0.25% = INR 250 |
| Daily soft stop | 1.00% = INR 1,000 |
| Daily hard lock | 1.50% = INR 1,500 |
| Maximum simultaneous positions | 3 |
| Maximum correlated full-risk positions | 1 risk unit per sector/theme |
| MCX simultaneous directional positions | 1 unless portfolio correlation engine approves more |

Suggested confidence-to-risk mapping:

```text
90-100 + all hard gates pass -> up to 0.75% risk
80-89  + all hard gates pass -> up to 0.50% risk
70-79  + no hard conflict    -> up to 0.25% probe risk
below 70                    -> WAIT or REJECT, quantity zero
```

The exceptional 0.75% tier is unavailable when source authority, freshness, liquidity, slippage, correlation, event risk, or emotional safety is not fully confirmed.

## 4. Emotional Safety Defaults

Recommended deterministic behavior:

| Event | State | Action |
| --- | --- | --- |
| One realized loss | WAIT_EMOTIONAL | 15-minute cooldown; monitoring remains available |
| Two consecutive realized losses | WAIT_EMOTIONAL | 30-minute cooldown and new setup review |
| Three consecutive losses | LOCKED_NO_TRADE | No new entries for the rest of the session |
| Daily loss reaches INR 1,000 | RISK_REDUCED | New risk reduced by 50% |
| Daily loss reaches INR 1,500 | LOCKED_NO_TRADE | No same-day manual override |
| New order attempted within cooldown | REJECT_REVENGE_RISK | Bot must reject the order |
| Position increased after invalidation | STOP_TRADING_NOW | Cancel new-entry permission and require review |
| Price is more than 1 ATR beyond planned entry | WAIT_FOMO | Wait for a new structure; do not chase |

Unlock rules:

- cooldown states unlock only after their timer and a new valid setup snapshot;
- daily hard lock unlocks only at the next valid trading session;
- parser, source, or model safety locks unlock only after deterministic validation passes;
- ML cannot unlock emotional or hard loss limits.

## 5. Universe Policy

The catalog may contain all NSE-listed instruments and all MCX contracts, but the executable scan universe must be filtered before expensive calculations.

```text
all listed instruments
  -> active/security-status filter
  -> price and liquidity filter
  -> traded-value and spread filter
  -> ASM/GSM/ban/delivery/expiry filter
  -> near-month/liquid-contract filter for MCX
  -> setup scan
  -> confirmation gates
  -> risk engine
  -> bot-safe output
```

Illiquid cash stocks, suspended securities, stale contracts, far-month contracts with weak depth, and contracts near physical-delivery risk must remain visible as rejected/watch records but cannot become READY.

## 6. OpenAlgo Bot Contract

TrendForge does not directly place an order. It publishes a trade intent to the existing bot.

Only `READY` or `PRIORITY_RADAR_READY` may be executable. All other states must carry `executable=false`.

Required output fields:

```text
signal_id
strategy_version
symbol
exchange
instrument_token or contract identity
timeframe
direction
state
executable
generated_at
data_cutoff_at
expires_at
entry_type
entry_price or trigger
protective_stop
targets
calculated_quantity
maximum_quantity
rupee_risk
account_risk_percent
expected_slippage
source_snapshot_ids
parser_output_ids
gate_decision_ids
source_authority
freshness_state
confidence_score
confidence_calibration_version
reason_codes
invalidation_reason
```

Before execution, the bot must independently revalidate:

- signal ID has not already been executed;
- signal has not expired;
- live price has not exceeded the allowed entry slippage;
- stop and quantity still obey account risk;
- daily loss and emotional locks are clear;
- required margin and lot size are valid;
- no new correlation or sector conflict exists;
- instrument/expiry identity exactly matches the signal.

## 7. Data Retention Defaults

Recommended local retention balances ML value against disk growth:

| Data | Retention |
| --- | --- |
| EOD candles | 10 years or all available history |
| Raw 1-minute candles for liquid/F&O universe | 12 months |
| Resampled 5m/15m/30m/1h/4h candles | 5 years |
| MCX intraday near-month candles | 24 months |
| Official raw reports and filings | 7 years, compressed and hash-addressed |
| Parser outputs and gate decisions | 7 years |
| Scanner candidates and ML snapshots | 5 years |
| Outcome labels and aggregate performance | Indefinite |
| Application logs | 90 days active, 1 year compressed audit logs |

Retention deletion must never remove an artifact still referenced by a scanner run, model-training dataset, trade decision, or outcome label.

## 8. Scan Completion Targets

Initial measurable targets:

| Scan | Target |
| --- | ---: |
| Full NSE EOD research scan | under 15 minutes |
| Intraday liquid-universe refresh | under 60 seconds |
| Active watchlist refresh | under 10 seconds |
| MCX active-contract refresh | under 10 seconds after source update |
| Candidate detail recalculation | under 2 seconds from cached inputs |
| Bot trade-intent response | under 500 ms after completed gate state |

Free/unofficial fallback sources have no production latency guarantee and cannot unlock executable output.

## 9. Failure And Stale-Data Policy

Last valid data remains visible with:

```text
source_data_date
retrieved_at
age
freshness_state
source_authority
parser_version
schema_hash
```

Rules:

- stale data is visible but cannot unlock a freshness-required gate;
- a new unparsed snapshot blocks use of an older parse for current READY;
- a skipped fetch must not overwrite or hide the last valid snapshot;
- metadata-only pages cannot substitute for structured report rows;
- valid empty reports require source-specific proof that empty is meaningful;
- source failure must downgrade only affected markets/gates, not fabricate zero values;
- official source failure cannot be silently replaced by unofficial data for executable decisions.

## 10. Backtest And Promotion Standard

A setup cannot move from research-only to executable READY until all of the following pass:

```text
point-in-time data with no lookahead
corporate-action adjusted stock data
survivorship-bias controlled universe
fees, spread, slippage, taxes, and realistic fills included
walk-forward or anchored out-of-sample validation
separate results by market regime, timeframe, and liquidity bucket
paper-trading/shadow validation after backtest
```

Preferred minimum thresholds:

| Requirement | Intraday | Swing |
| --- | ---: | ---: |
| Minimum closed trades per setup family | 500 | 200 |
| Minimum history | 2 years | 5 years |
| Out-of-sample share | at least 30% | at least 30% |
| Expectancy after costs | greater than 0.15R | greater than 0.20R |
| Profit factor | at least 1.20 | at least 1.25 |
| Maximum strategy drawdown | at most 8% | at most 10% |
| Paper/shadow period | 30 sessions and 100 signals | 60 sessions and 50 signals |

Win rate alone cannot promote a setup. Confidence buckets must be calibrated: a displayed 80% bucket should achieve a realized target-hit probability within a predefined tolerance, initially plus or minus 10 percentage points.

## 11. Parser And Model Rollback Policy

ML learns from failures but is not the rollback mechanism.

Deterministic rollback rules:

1. Every parser, gate definition, feature schema, model, and strategy has a version.
2. Schema mismatch immediately quarantines the new artifact.
3. The last valid artifact remains visible as stale, but cannot masquerade as current.
4. The affected READY gate is blocked.
5. Raw source data is retained for replay.
6. A corrected parser must replay historical raw snapshots and pass regression fixtures.
7. Model degradation switches execution back to the last approved champion or to research-only mode.
8. ML may identify failure clusters and propose features; it cannot autonomously promote itself or relax a gate.

## 12. Verified Present Runtime State

Verified on 2026-07-10:

```text
API listening: http://127.0.0.1:8001
API mode: mock-data
Backend tests: 31/31 pass
Frontend static checks: 65/65 pass
Python compile: pass
SQLite integrity_check: ok
SQLite foreign_keys: disabled
Structured live domain rows:
  CFTC COT: 11
  MWPL: 0
  Participant OI: 0
  NSE large deals: 0
  AMFI: 0
  MCX bhavcopy: 0
Readiness:
  G12 smart money: blocked
  G13 OI/MWPL/basis: blocked
  MCX context: blocked
```

The passing tests prove that the prototype runs. They do not prove trading correctness or production readiness.

## 13. Critical Audit Findings

### P0 - Must Fix Before Any Executable Bot Output

1. Backend and frontend still contain mock READY candidates and trade levels.
2. API failure silently falls back to fake READY candidates without a dominant demo banner.
3. G12 can pass from one large-deal source alone.
4. G13 can pass from MWPL alone without stock OI, futures basis, rollover, IV, or options evidence.
5. NSE participant futures OI fields are double-counted by overlapping column matching.
6. NSE participant options are interpreted as generic long-minus-short, ignoring call/put direction.
7. NSE large-deal parser misreads official-style `Client Name` plus `Buy/Sell` rows as buyer=`BUY`, seller=`BUY`.
8. Harmonic XAD is calculated from D-A instead of the X-D relationship to XA.
9. Harmonic pivots use future candles without persisting the later pivot-confirmation timestamp, creating backtest lookahead risk.
10. Snapshot readiness does not require the parse to belong to the latest snapshot.

### P1 - Data Integrity And Reliability

11. A `fetch=false` check writes a new SKIPPED snapshot and hides prior valid source state.
12. Valid-empty source rules exist in one module but are rejected in gate readiness.
13. Stored OHLCV reads can mix multiple sources and duplicate timestamps.
14. Revised official candles cannot replace temporary candles because storage uses insert-ignore behavior.
15. Parquet refresh overwrites the complete symbol file instead of merging history.
16. Parquet path components are not fully sanitized for Windows path traversal.
17. NSE custom 4H completeness divides candle count by minutes; a valid 48-bar morning session is reported as 20% complete.
18. Generic yfinance 4H resampling is midnight-anchored rather than NSE-session anchored.
19. Corporate-action adjustment is absent from harmonic and backtest inputs.
20. The source resolver accepts file-looking URLs without sufficiently validating content type/schema.
21. MWPL resolver prefers the ban-only file before percentage files, so structured MWPL may never be reached.
22. Bulk and block files are alternatives under one snapshot instead of separate required artifacts.
23. AMFI parser cannot correctly process the normal multi-sheet XLS/XLSX disclosure workflow.
24. CFTC regime logic treats Managed Money and Commercials having the same sign as bullish, despite commercial positioning requiring percentile/contrarian interpretation.
25. MCX parser stores only close/volume/OI, not complete official OHLC/settlement/contract identity.

### P1 - Scanner, ML, And Operations

26. The all-universe scheduler only slices five mock candidates; it does not scan NSE or MCX universes.
27. Scanner runs are not transactionally persisted with all candidates and gate artifacts.
28. Candidate rows do not persist direct source snapshot, parser output, and gate-decision IDs.
29. No outcome-labelling worker exists.
30. No point-in-time feature engineering or full backtest engine exists.
31. No persistent account/risk settings exist.
32. No OpenAlgo trade-intent contract exists.
33. SQLite foreign keys, WAL, busy timeout, migration versioning, and durable scheduler locking are absent.
34. Raw archives, candidates, alerts, and pattern rows have no retention/deduplication policy.
35. Project dependencies are not isolated or locked; the shared Python environment reports dependency conflicts.
36. Frontend static tests check that strings/functions exist but do not test real interaction, XSS, stale presentation, or responsive rendering.
37. API/source-derived values are injected using `innerHTML`, creating an XSS risk.
38. CORS permits all origins.
39. There is no authentication or bot API token, even for future local automation.
40. Visual browser verification was blocked during the audit by the Windows sandbox helper failure.

## 14. Source And Link Coverage Truth

Current project text contains 194 unique HTTP/HTTPS links.

```text
Runtime/reference code links: 69
Documentation-only links: 125
Structured parser mappings: 7
Live structured parser families with stored rows: CFTC only
```

Saving a URL is not integration. A source is integrated only when it has:

```text
legal/authority classification
stable resolver contract
raw archive
content-type validation
structured parser
schema validation
source data date
freshness policy
row-level persistence
scope restriction
gate wiring
fixtures from real official files
failure tests
```

## 15. Open-Source Components To Evaluate

These are candidates, not automatic dependencies:

- Pandera for strict DataFrame and report schema validation;
- pandas-market-calendars for NSE sessions and holidays, with locally verified exchange dates;
- APScheduler with a persistent job store for durable EOD and intraday scheduling;
- vollib/py_vollib-compatible pricing functions for Black/Black-Scholes/Black-Scholes-Merton IV and Greeks;
- DuckDB for local analytical queries over partitioned Parquet;
- Hypothesis for property-based parser, candle, ratio, and risk-engine testing;
- structlog or standard-library JSON logging for correlation-ID audit logs.

Libraries never replace source authority, freshness, exchange calendar verification, or deterministic risk limits.

<a id="current-build-order"></a>

## 16. Build Order

### Milestone 0 - Safety Foundation

- remove or clearly isolate mock READY output;
- make API-offline UI fail closed with no trade candidates;
- correct G12/G13/MCX gate contracts;
- add strict machine-readable output states and `executable` flag;
- add regression tests proving no mock/stale/unofficial output can reach the bot.

### Milestone 1 - Parser Correctness And Lineage

- replace loose substring field matching with source-versioned schemas;
- fix participant OI and large-deal parsing;
- require parse `snapshot_id` to match current snapshot;
- separate bulk, block, ban, MWPL, and report artifacts;
- add real official-file fixtures and schema quarantine.

### Milestone 2 - Candle And Harmonic Integrity

- isolate candle sources and select one authoritative series per scan;
- upsert corrected candles with revision history;
- merge/dedupe partitioned Parquet;
- fix NSE timezone/session/4H completeness;
- fix harmonic ratios, PRZ construction, invalidation, targets, and pivot confirmation timestamps;
- add no-lookahead pattern tests.

### Milestone 3 - Remaining Official Source Framework

- NSE SLB;
- NSE F&O bhavcopy, stock OI, basis, expiry and rollover;
- NSE corporate actions and buybacks;
- BSE buyback/open offers and corporate disclosures;
- SEBI PIT/SAST/pledge structured filings;
- AMFI XLS/XLSX holdings and true adjusted month-over-month deltas;
- MCX full bhavcopy contracts;
- CFTC historical percentiles;
- required global MCX inputs including USD/INR.

### Milestone 4 - Real EOD And Intraday Scanner

- build all-NSE and active-MCX universe services;
- add liquidity and tradability prefilter;
- add durable market-calendar-aware scheduler;
- connect OpenAlgo data through a versioned adapter;
- keep all unofficial/free fallback scans research-only.

### Milestone 5 - Risk, Bot Integration, And Safety

- persist account and risk settings;
- implement position sizing and correlation caps;
- implement emotional/daily loss state machine;
- add signed/idempotent OpenAlgo trade-intent API;
- make the bot perform final pre-order validation.

### Milestone 6 - ML, Outcomes, And Promotion

- persist point-in-time feature vectors;
- label trigger, MAE, MFE, target, stop, expiry, and invalidation outcomes;
- implement walk-forward backtests and confidence calibration;
- add champion/challenger model registry;
- prohibit autonomous ML promotion or gate relaxation.

### Milestone 7 - Production Hardening

- isolated locked environment;
- migrations, WAL, foreign keys and backup restore tests;
- structured logging and monitoring;
- restricted CORS and localhost bot token;
- retention and archive verification;
- browser E2E, accessibility, responsive, load, chaos and recovery tests.

## 17. Current Authorization Boundary

The user authorized the guarded local research build for both NSE stocks and MCX, intraday and swing, using an INR 1,00,000 account profile. That implementation has started and the verified status is recorded below.

This authorization does not permit broker execution. The following remain explicitly deferred to the final phase:

1. verified live official/licensed market data and official production download contracts;
2. real OpenAlgo credentials, broker mapping, order placement and broker-state reconciliation;
3. shadow/paper validation before any live order permission.

Until those are complete, TrendForge may emit research WAIT/REJECT results and deterministic sizing demonstrations, but it must expose zero executable READY trade intents.

## 18. Production Hardening Execution - 2026-07-10

### Verified Implemented

- mock candidates are isolated as `WAIT_DEMO_DATA`; the stored-data scanner never emits executable READY;
- locally stored SQLite and Parquet candles feed the harmonic research scanner;
- pyharmonics is guarded by an internal ratio/gate validator and G00-G14 proof output;
- full scan candidates, source lineage, point-in-time features and cutoffs are stored for future ML work;
- raw source snapshots, parser outputs, source freshness, row-level domain tables, scanner runs and candidates are persisted;
- structured parsers exist for CFTC COT, NSE MWPL/ban, participant OI, large deals, F&O bhavcopy, SLB, AMFI, NSE/BSE corporate events, SEBI structured disclosures and MCX bhavcopy;
- parser outputs are fail-closed unless the latest raw snapshot is structured, dated, fresh, schema-valid and scope-compatible;
- participant OI is market/regime context only, CFTC is delayed commodity regime context, and SLB is a borrow-pressure proxy only;
- the source scheduler and all-universe scan framework are controlled, overlap-locked, persisted and off by default;
- deterministic position sizing, INR 1,00,000 risk settings, no averaging down, daily lock and portfolio-count limits are implemented;
- Black-Scholes-Merton price, Greeks and bounded implied-volatility calculations are implemented, but live option evidence remains unavailable until synchronized quotes exist;
- expanding-prefix harmonic validation uses no future candles and applies a conservative stop-first same-bar rule;
- CFTC disaggregated history is archived from official annual files and converted into point-in-time weekly deltas, 13/26/52/156-week means, 52/156-week z-scores, 52/260-week percentiles, crowding and optional price-divergence context;
- `kustex/CFTC-COT-Report` is saved as `REFERENCE_ONLY_ANALYTICS`; it cannot unlock READY and its Dash/downloader/email stack is not installed;
- SQLite uses WAL, foreign keys on application connections, a 5-second busy timeout and integrity-checked local storage;
- FastAPI has localhost-only CORS, bounded inputs, request IDs and structured request logging;
- the single-panel frontend escapes untrusted text and exposes parser drilldown, raw/source state, scanner status, risk profile and time-safe backtesting.

### Runtime Evidence

```text
backend tests: 55 passed
frontend acceptance checks: 74/74 passed
clean isolated environment: pip check clean, 55 tests passed
Python compilation: passed
JavaScript syntax: passed
SQLite integrity: ok; journal_mode=wal; application foreign_keys=1
dashboard: no console warning/error; no overflow at 1440x900 or 390x844
live local API: http://127.0.0.1:8001/
radar READY rows: 0
stored scan: COMPLETE, 2 series, 2 non-executable candidates
harmonic validation: NO_PATTERNS on current RELIANCE 1d sample, no result invented
CFTC archive: 2021-01-05 through 2026-06-30, 287 weekly dates, 3,170 position/features rows
CFTC current state: WAIT_STALE_DATA because the latest official archived position date is 2026-06-30
```

### Honest Remaining Boundary

The build is production-shaped but not production-ready for automated trades. Remaining work is deliberately concentrated into:

1. live-contract verification and population for official NSE/BSE/AMFI/SEBI/MCX/CFTC/global inputs, plus a legal intraday feed and full exchange universe/instrument masters;
2. OpenAlgo adapter integration with credentials supplied by the user, idempotent intents, final quote/margin/position revalidation, paper/shadow operation and an explicit live kill switch.

No ML model may learn around missing evidence or promote a blocked candidate. ML records failures and improves ranking only after point-in-time outcomes exist.

## Full Historical Verbatim Appendix

The following source documents are embedded verbatim so no historical requirement, example, reasoning note or audit statement is lost. These appendices are historical evidence; the active sections above control implementation when statements conflict.

<!-- HISTORICAL_SOURCE_BEGIN path=backup_reference_20260705_162956/backup_screener_rules.md sha256=ee35a478d9358193e74ca56c271c42cdb4a68fcf73ffa004d56ac5d1b70a8bcb lines=3986 -->
# TrendForge Screener Rules, Purpose, Logic, And Reason

## 1. Purpose

TrendForge is a local NSE stock screener that produces a small morning shortlist of the strongest actionable trending stocks.

The goal is not to find stocks where indicators already look bullish. The goal is to detect real trend formation before the obvious late-stage crowd signal by checking the cause of the move, the sponsor behind the move, the chart structure, and live money flow.

The screener must answer four practical trader questions for every stock:

1. Why is this stock moving?
2. Who is behind the move?
3. Is the chart structure ready?
4. Is money moving right now?

If TrendForge cannot explain the move with evidence, it must not pretend confidence.

## 2. Target User

The first user is an active Indian market trader who wants a daily NSE shortlist for swing and intraday opportunities.

The user does not want a noisy table of 50 technical signals. The user wants 3 to 8 high-quality candidates with a plain-English reason, entry area, stop, target, risk sizing, and trap warnings.

## 3. Core Business Outcome

TrendForge must reduce manual market scanning across broker terminals, NSE pages, AMFI data, Screener.in, news sites, and charts.

The business outcome is a faster and more evidence-driven trading preparation workflow:

- Less time checking many websites manually.
- Fewer late breakout entries.
- Fewer operator-pump and illiquid-stock traps.
- Clearer explanation of why a stock is shortlisted.
- Better discipline through risk sizing, exit rules, and journaling.

## 4. Core Philosophy

Price is treated as a symptom, not the root cause.

The causal chain is:

1. Someone knows or expects something.
2. They decide to act.
3. They buy or sell in size.
4. Order-flow imbalance appears.
5. Price moves.
6. Indicators react after price has already moved.
7. Retail traders chase the visible signal.

TrendForge must focus on steps 1 to 4. RSI, MACD, moving averages, and breakouts can support evidence, but they must not be the main reason a stock qualifies.

## 5. Mandatory 4-Layer Qualification Rule

Every stock must be tested against four independent evidence layers:

| Layer | Question | Pass Example | Fail Example |
| --- | --- | --- | --- |
| CAUSE | Is there a real reason for the move? | Earnings beat, order win, policy tailwind, sector boom | No catalyst or stale news |
| SPONSOR | Is serious money actually accumulating? | High delivery, promoter buying, MF buying, bulk deals | Low delivery, no institution footprint |
| STRUCTURE | Is the chart prepared for a controlled move? | VCP, tight base, relative strength, near 52-week high | Overextended, supply zone, weak RS |
| FLOW | Is money moving now? | RVOL by time of day, OI build, option activity, imbalance | Dead volume, no OI, no urgency |

A stock must pass at least 3 of 4 layers to appear in the final shortlist.

If fewer than 3 layers pass, the stock must be rejected or marked as watchlist-only.

## 6. Layer Scoring Rules

### 6.1 CAUSE Layer: 0 To 6 Points

Purpose: prove there is a real reason for the move.

| Evidence | Points | Rule |
| --- | ---: | --- |
| Verified catalyst | +3 | Earnings beat, order win, policy change, sector trigger, BSE/NSE filing, rating upgrade |
| Reflexive mechanism | +2 | Short squeeze, gamma effect, index inclusion, forced covering, rebalance |
| Multiple reinforcing catalysts | +1 | Two or more independent causes pointing same direction |
| No catalyst | 0 | Reject cause layer |

Cause evidence must include source and date.

Stale catalysts must decay. A catalyst already fully priced in must not score full points.

### 6.2 SPONSOR Layer: 0 To 10 Points

Purpose: identify whether real informed money is accumulating.

Sponsor is the most important layer.

| Evidence | Points | Rule |
| --- | ---: | --- |
| Delivery above 40 percent on up-days | +2 | Real buying, not only speculation |
| Promoter open-market buying in last 30 days | +3 | Highest-information actor buying |
| Named super-investor or major bulk deal | +2 | Smart-money footprint |
| FII/DII 5-day sector alignment | +1 | Larger flow supports sector |
| Multiple mutual funds adding | +2 | Institutional conviction |
| Wyckoff absorption bars | +2 | High volume with controlled price move suggests accumulation |

Sponsor evidence must decay with age:

- 0 to 7 days: full weight.
- 8 to 14 days: moderate decay.
- 15 to 30 days: heavy decay.
- More than 30 days: watchlist context only unless repeated.
- Mutual fund data starts with lower weight because it is naturally delayed.

### 6.3 STRUCTURE Layer: 0 To 6 Points

Purpose: prove the stock has a chart structure capable of a clean move.

| Evidence | Points | Rule |
| --- | ---: | --- |
| VCP or tight consolidation base | +2 | Supply contraction before expansion |
| True relative strength | +2 | Stock strong while Nifty or sector is weak |
| Multi-timeframe alignment | +1 | Daily, weekly, and monthly do not conflict |
| Within 25 percent of 52-week high | +1 | Lower overhead supply |

Structure must fail or downgrade when:

- Stock is already too extended.
- Price is pushing into major resistance.
- Move is vertical without base.
- Higher timeframe conflicts with lower timeframe.

### 6.4 FLOW Layer: 0 To 6 Points

Purpose: prove money is active right now.

| Evidence | Points | Rule |
| --- | ---: | --- |
| RVOL by time-of-day above 2.0 | +2 | Activity is unusual for the current time |
| Call OI building at key strikes | +2 | Options market supports direction |
| Favorable gamma exposure | +1 | Market-maker mechanics can amplify move |
| Cross-market driver aligned | +1 | External market confirms stock driver |

Flow must be time-aware. A high-volume full-day reading is not enough for intraday logic unless it is normalized by time of day.

## 7. Hard Reject Rules

A stock must be removed before scoring if it is unsafe to trade.

Reject if any of these are true:

- In F&O ban when the planned trade depends on derivatives.
- Under ASM or GSM surveillance.
- Illiquid by turnover threshold.
- Micro-cap below the configured market-cap floor.
- Within 2 percent of circuit limit.
- Promoter pledge above configured danger threshold, default 50 percent.
- Data is stale and no fallback source confirms it.
- Corporate action adjustment is missing for price history.
- Known pump-like behavior with no sponsor evidence.

Default liquidity thresholds:

- Swing trading: daily turnover should usually be above INR 20 crore.
- Intraday trading: daily turnover should usually be above INR 50 crore.

These are defaults and must be configurable.

## 8. Market Context Comes First

No stock should be evaluated in isolation.

TrendForge must first compute:

- GIFT Nifty pre-market direction.
- Nifty trend and regime.
- India VIX behavior.
- FII/DII flow.
- Market breadth.
- Sector leadership.
- Global drivers such as crude, USD, DXY, S&P, Nasdaq, gold, and relevant commodities.

If market context is hostile, individual stock scores must be downgraded or marked with caution.

Examples:

- Nifty green but breadth weak: block low-quality breakouts.
- VIX spike: reduce position size or block fresh entries.
- Sector weak: downgrade long ideas inside that sector.
- Global driver conflict: downgrade driver-sensitive stocks.

## 9. Independence Rule

TrendForge must avoid fake confidence from duplicated evidence.

If two layers use the same raw evidence, the second signal must be penalized.

Example:

- FLOW uses volume.
- STRUCTURE uses volume-confirmed breakout.
- These cannot be counted as two fully independent confirmations.

The independence matrix must track shared raw inputs and reduce duplicate scoring.

Required raw-input tags:

- price
- volume
- delivery
- options
- news
- filings
- institutional-holding
- sector-flow
- global-driver
- market-breadth

## 10. Staleness And Evidence Decay

Every evidence item must carry:

- source
- timestamp
- freshness status
- confidence
- decay factor

Fresh evidence scores higher than old evidence.

Rules:

- Live price and volume must be current or marked stale.
- Delivery data is usually previous-day data.
- Mutual fund holdings are delayed and must start with reduced weight.
- Promoter and bulk-deal evidence decays over time.
- News that caused the move days ago must not be treated like a fresh catalyst.

If the data freshness cannot be proven, the system must mark the result as uncertain.

## 11. Shortlist Rules

The final shortlist should usually contain 3 to 8 actionable stocks.

Each shortlisted stock must include:

- rank
- stock symbol and name
- direction
- total score
- layer score breakdown
- passed layers
- failed or weak layers
- entry area
- stop-loss
- target
- risk-reward
- suggested position size
- plain-English WHY
- evidence citations with source and date
- trap warnings
- data freshness status

If more than 8 stocks qualify, rank by:

1. Sponsor strength.
2. Cause quality.
3. Structure quality.
4. Flow urgency.
5. Risk-reward.
6. Relative strength percentile.

If zero stocks qualify, TrendForge must say no-trade instead of weakening rules silently.

## 12. Reasoning Output Rules

The WHY paragraph must be specific, not generic.

Bad:

"Stock is bullish because volume is high and trend is strong."

Good:

"XYZ qualifies because promoters bought INR 2 crore 12 days ago, delivery was 48 percent on the last two up-days, two mutual funds added last month, price is coiling in a VCP base near a 52-week high, and current RVOL is 2.3x by time of day. Cause is Q2 earnings beat plus raised guidance."

Reasoning must include:

- who is likely behind the move
- what caused the move
- why the setup is ready or not ready
- what live flow confirms
- what could invalidate the trade
- what evidence is missing

When evidence conflicts, the output must say WAIT.

## 13. Risk Rules

TrendForge is not allowed to output a stock pick without risk controls.

Every actionable candidate must include:

- entry zone
- invalidation level
- stop-loss
- target
- minimum 2:1 risk-reward unless explicitly configured otherwise
- position size based on account capital and risk per trade
- slippage check
- sector concentration check
- event-risk warning

Position sizing must consider:

- account size
- risk per trade
- stop distance
- market regime
- liquidity
- open portfolio correlation
- setup quality

Default risk:

- Intraday: 0.5 percent account risk per trade.
- Swing: 1 percent account risk per trade.

These defaults must be configurable.

## 14. Exit Rules

Every trade idea must include an exit plan.

Supported exit logic:

- fixed stop-loss
- ATR or Chandelier trailing stop
- time stop when price does not move after configured candles
- profit booking ladder
- regime-change kill switch
- VIX spike warning
- sector breakdown warning

No candidate should be shown as "buy and hope."

## 15. Data Source Rules

Primary free data sources:

| Source | Use |
| --- | --- |
| Upstox API | live price, historical candles, option chain, WebSocket |
| Angel One SmartAPI | backup broker data |
| NSE website | delivery, FII/DII, bulk/block deals, ban list, ASM/GSM, bhavcopy |
| AMFI | mutual fund holdings |
| Screener.in | fundamentals, promoter holding, pledge, shareholding |
| GIFT NSE | pre-market Nifty direction |
| Yahoo Finance | global markets and macro drivers |
| Trendlyne | insider trades and super-investor portfolios |

The system must degrade gracefully when a source fails.

Fallback examples:

- Upstox unavailable: use Angel One.
- Pre-open unavailable: use NSE public JSON.
- NSE pre-open unavailable: estimate from GIFT Nifty and mark confidence lower.
- Sponsor data unavailable: do not fake Sponsor score.

## 16. Scraping Rules

NSE scraping is fragile and must be treated as a failure-prone dependency.

The scraper must include:

- cookie management
- realistic headers
- retry with exponential backoff
- request throttling
- source health checks
- structured error logging
- cached last-good data
- fallback source routing

If scraping breaks, the system must show data-health warnings instead of producing false confidence.

## 17. Feedback And Calibration Rules

Initial scoring weights are assumptions until validated by real outcomes.

TrendForge must journal outcomes and calibrate weights over time.

Track:

- score at entry
- layer score breakdown
- setup type
- sector
- market regime
- entry
- stop
- target
- exit
- P&L
- R multiple
- reason for exit

Calibration views required:

- hit rate by score bucket
- average R by score bucket
- hit rate by setup type
- hit rate by sector
- hit rate by regime
- false positive reasons

Weights should be changed only after enough sample size exists.

## 18. Backtesting Rules

Backtests must avoid cheating.

Mandatory:

- point-in-time correct data
- corporate-action adjustment
- no look-ahead data
- delisted-stock inclusion when possible
- transaction costs
- slippage model
- survivorship-bias warnings
- separate in-sample and out-of-sample testing

Backtest output must be treated as validation, not proof.

## 19. Alerts Rules

Alerts must be evidence-based.

Supported alerts:

- pre-market market-bias alert
- gap alert
- score-qualified alert
- stop-hit alert
- target-hit alert
- regime-change alert
- stale-data alert
- source-failure alert

Alert text must include reason and risk, not only symbol.

## 20. Dashboard Rules

The dashboard is a control room, not a marketing page.

Required panels:

- macro bar
- regime panel
- sector heatmap
- shortlist table
- stock detail
- options panel
- driver confirmation
- exit engine
- funnel view
- journal
- How It Works page

The shortlist table is the primary screen.

The UI must make it easy to answer:

- What should I focus on today?
- Why did it qualify?
- What layer is weak?
- What is the risk?
- What can go wrong?
- Is the data fresh?

## 21. What TrendForge Must Not Do

TrendForge must not:

- auto-place orders in the first version
- claim price prediction certainty
- treat AI output as a trading signal without evidence
- use social media sentiment as a primary trigger
- ignore stale data
- hide source failures
- output buy/sell without risk
- rank illiquid or manipulated stocks as actionable
- silently relax filters to force candidates
- expose or hardcode API keys

Auto-order execution is intentionally out of scope until legal, broker, audit, risk, and SEBI Algo-ID requirements are handled.

## 22. Minimum MVP

The first usable MVP should include:

1. Local database.
2. NSE universe and basic candle ingestion.
3. Data health checks.
4. Market context engine.
5. Tradability filter.
6. 4-layer causal score.
7. Plain-English WHY output.
8. Basic risk output.
9. CLI or simple API endpoint returning shortlist.
10. Tests for scoring, staleness, independence, and reject rules.

The dashboard can come after the brain produces reliable output.

## 23. Build Order

1. Data plumbing.
2. Market context engine.
3. Tradability filter.
4. 4-layer causal engine.
5. Risk engine.
6. Backend API and alerts.
7. Frontend dashboard.
8. Feedback loop and calibration.

Each step must be independently usable and testable.

## 24. Phase-Gate Rule

Before coding each milestone, the following must be clear:

- exact input data
- exact output contract
- reject conditions
- stale-data behavior
- test cases
- failure behavior
- acceptance criteria

No implementation should start from vague intent.

## 25. Acceptance Criteria For The Screener Brain

The screener brain is acceptable only when:

- it can scan the configured NSE universe
- it rejects dangerous stocks before scoring
- it scores CAUSE, SPONSOR, STRUCTURE, and FLOW separately
- it requires at least 3 of 4 layers to qualify
- it applies staleness decay
- it applies independence penalties
- it outputs evidence citations
- it produces a ranked shortlist
- it outputs no-trade when nothing qualifies
- it gives risk controls for each actionable candidate
- it logs data-source and scoring failures clearly

## 26. First Decisions Still Needed

These must be answered before implementation:

1. Project location: should TrendForge live in `D:\TrendForge` or inside an existing trading app?
2. First data mode: live Upstox/Angel keys now, or NSE-scraped/offline mode first?
3. First interface: CLI output first, API first, or dashboard first?
4. Market scope: NSE cash only first, or NSE cash plus F&O?
5. Trading style: intraday first, swing first, or both with separate scoring profiles?
6. Account profile: approximate capital and max risk per trade.
7. Alerts: dashboard-only first, or Telegram from v1?


## 27. Verified Merge From Second Source Document

The second source document was verified line by line and merged into this master rule file.

The important correction is this:

TrendForge is not only a 4-layer stock scorer. It is a time-sequenced decision engine where each layer gates the next layer.

Runtime decision order:

1. Global macro and overnight context.
2. Market regime and direction.
3. Sector selection.
4. Stock universe filtering and tradability.
5. Setup identification.
6. Confirmation and multi-factor edge.
7. Risk engine and position sizing.
8. Execution and order management.
9. Post-entry monitoring and exit.

The older CAUSE, SPONSOR, STRUCTURE, and FLOW model remains the core causal scoring engine, but it must run inside this larger gated sequence.

Hard rule:

- Do not check indicators before context.
- Do not identify setups before tradability.
- Do not enter from setup alone.
- Do not output actionable trades before risk and execution checks.
- If a gate fails, the stock is rejected, downgraded, or marked WAIT.

## 28. Gate Types

Every runtime rule must classify its result as one of these gate outputs:

| Gate Output | Meaning | Action |
| --- | --- | --- |
| PASS | Evidence supports proceeding | Continue to next layer |
| SOFT_FAIL | Evidence is weak or mixed | Downgrade score, reduce size, or watchlist only |
| HARD_FAIL | Unsafe, untradeable, or invalid | Reject immediately |
| WAIT | Evidence conflict or timing not ready | Do not trade yet |
| STALE | Required data is old or unverified | Block action unless fallback confirms |

No layer may silently ignore a failed upstream gate.

## 29. Layer 0 Runtime Rules: Global Macro And Overnight Context

Layer 0 runs the evening before and again from 6:00 AM to 9:00 AM IST.

Purpose:

- decide the global battlefield before individual stocks are considered
- avoid blindly following technical setups during hostile macro conditions
- separate US-market influence from India-specific flow and policy

### 29.1 NSE Is Not A Direct Copy Of US Markets

Nifty often responds to US and European overnight moves, but it is not a 1:1 copy.

Rules:

- Treat US direction as an influence, not a command.
- Use GIFT Nifty for expected Indian open direction.
- Use FII/DII flow to judge whether India can absorb or amplify global moves.
- Use sector-specific logic because IT, banking, FMCG, pharma, metals, and PSU sectors react to different drivers.

Failure mode:

- US market falls, but strong DII buying or India-specific positive news causes Nifty to recover after a weak open.

Avoidance:

- Never use US data alone.
- Cross-check US market, GIFT Nifty, FII/DII, Asian markets, and Indian event calendar.

### 29.2 GIFT Nifty Usage

| Time IST | Use |
| --- | --- |
| 6:00 AM to 9:00 AM | Best pre-market direction signal |
| 9:00 AM to 9:15 AM | Gap size estimation with NSE pre-open |
| After 9:15 AM | Lower value because NSE futures and cash market take over |

Rules:

- GIFT Nifty premium or discount to previous Nifty close estimates gap size.
- GIFT Nifty is not guaranteed; pre-open can modify the final open.
- If GIFT Nifty is more than +0.5 percent, prepare long watchlist.
- If GIFT Nifty is between -0.2 percent and +0.2 percent, stay neutral and wait for pre-open.
- If GIFT Nifty is below -0.5 percent, prepare short or defensive watchlist.
- If GIFT Nifty is beyond +/-1.0 percent, prepare gap-and-go or gap-fill scenarios, not blind entries.

### 29.3 Overnight US And Global Checks

Required checks:

| Check | Meaning |
| --- | --- |
| S&P 500 close | broad US risk direction |
| Nasdaq close | Indian IT sentiment proxy |
| US VIX | global fear gauge |
| US 10Y yield | pressure on growth stocks and FII appetite |
| DXY | rising dollar can pressure India and FII flows |
| US futures at 6 AM IST | live recovery or continuation signal |
| Fed commentary | hawkish or dovish global liquidity signal |

Failure modes:

- India-specific events override US direction.
- Sector rotation makes US tech weakness irrelevant to Indian banking or FMCG.
- Strong domestic buying absorbs foreign selling.

### 29.4 Intermarket Driver Map

| Driver | NSE Impact | Sectors |
| --- | --- | --- |
| Brent crude up | negative for India as net importer | OMCs, paints, airlines, chemicals; ONGC may benefit |
| Gold up | risk-off context, positive for gold financiers | Titan, Muthoot, Manappuram |
| USD/INR up, rupee weak | positive exporters, negative importers | IT benefits; auto/API importers hurt |
| China weakness | metals demand risk, China+1 opportunity | metals negative; electronics manufacturing can benefit |
| Nikkei/Hang Seng | Asian sentiment | broad market |
| DAX/FTSE pre-open | confirms or denies US signal | broad market |
| India 10Y yield up | banks may benefit, NBFCs and realty may suffer | banking, NBFC, realty |

Rule:

Use intermarket data as context and sector filter, not as a direct trade signal.

### 29.5 FII/DII Flow Rules

FII/DII flow is a critical India-specific signal.

Track:

- FII cash net buy/sell.
- DII cash net buy/sell.
- FII derivative position.
- FII index futures long/short ratio.
- 5-day and 20-day rolling patterns.

Pattern interpretation:

| 5-Day Pattern | Meaning |
| --- | --- |
| FII buying + DII buying | strong bullish agreement |
| FII selling + DII buying | tug of war; domestic absorption |
| FII selling + DII selling | danger; nobody wants exposure |
| FII buying + DII selling | rotation; often medium-term bullish |

Failure modes:

- FII cash data is T+1.
- Single-day FII selling may be arbitrage or hedging.
- DII buying can be passive SIP flow, not active conviction.

Avoidance:

- Prefer rolling trends to single-day data.
- Cross-check cash flow with derivative positioning.

### 29.6 Event Calendar Rules

Hard blocks:

- Do not swing trade a stock with earnings within 3 sessions unless it is explicitly a PEAD setup.
- Do not trade on RBI policy day unless the strategy is specifically event-based.
- Do not trade stocks in F&O ban for derivative-dependent plans.
- Do not trade stocks added to ASM/GSM.

Warnings:

- Ex-dividend dates can distort price.
- F&O expiry week has rollover and gamma effects.
- SEBI or margin-rule changes can invalidate older assumptions.
- Company results, board meetings, policy news, and global events must be checked before action.

## 30. Layer 1 Runtime Rules: Market Regime And Direction

Layer 1 runs from 8:30 AM to 9:15 AM and continuously updates intraday.

Purpose:

- choose the right strategy family
- block breakout logic in hostile regimes
- size risk according to volatility and breadth

### 30.1 Regime Classification

| Regime | Identification | Strategy Bias |
| --- | --- | --- |
| Strong uptrend | Nifty > 20 DMA > 50 DMA > 200 DMA and India VIX < 15 | aggressive longs, breakouts, buy dips |
| Mild uptrend | Nifty > 50 DMA but 20 DMA weak or converging | selective longs |
| Range-bound | flat moving averages, support/resistance oscillation | mean reversion, reduce breakout activity |
| Mild downtrend | Nifty < 20 DMA and approaching 50 DMA | defensive, short rallies |
| Strong downtrend | Nifty < 50 DMA < 200 DMA and VIX > 20 | short-biased or cash |
| Crash/panic | VIX > 30, major support breaks, FII dumping | cash first, wait for stabilization |

### 30.2 India VIX Rules

| India VIX | Meaning | Action |
| --- | --- | --- |
| < 12 | complacency | breakouts may work, but spike risk rises |
| 12 to 16 | normal | standard sizing |
| 16 to 20 | elevated anxiety | tighten stops, reduce size |
| 20 to 25 | fear | expect reversals, reduce activity |
| > 25 | panic | only best setups, very small size or no trade |
| falling from high | fear cooling | supportive for longs |
| rising from low | calm breaking | caution |

Rule:

VIX adjusts sizing and stop placement. It is not a standalone direction signal.

### 30.3 Market Breadth Rules

Track:

- advance/decline ratio
- advance/decline volume
- new 52-week highs vs lows
- percent above 200 DMA
- percent above 50 DMA

Signals:

- Advance/decline above 2:1 is broad bullish participation.
- Advance/decline below 1:2 is bearish.
- More than 60 percent above 200 DMA is healthy.
- Less than 40 percent above 200 DMA is weak.
- Nifty up while breadth weak is a dangerous narrow rally.
- Nifty down while breadth strong can indicate bottoming behavior.

Failure mode:

- Breadth can weaken temporarily during genuine sector rotation.

Avoidance:

- Combine breadth with sector rotation and FII/DII flow.

### 30.4 Nifty Options Chain Rules

Options data confirms market regime; it does not lead the entire decision.

Track:

- max pain
- PCR
- highest call OI
- highest put OI
- change in OI
- long build-up
- short build-up
- short covering
- long unwinding

Direction matrix:

| GIFT Nifty | PCR | OI Direction | FII Stance | Verdict |
| --- | --- | --- | --- | --- |
| Green | > 1.0 | put OI adding lower | net buyer | strong buy bias |
| Green | < 0.8 | call OI adding above | net buyer | cautious buy, resistance near |
| Red | > 1.2 | put support holding | net seller | gap down but support possible |
| Red | < 0.7 | put OI unwinding | net seller | strong sell or stay cash |

Failure modes:

- OI can be T+1 or approximate intraday.
- Market makers can shift hedges quickly.
- Last 2 expiry days are unstable due to gamma.
- OI may be hedge inventory, not directional institutional bet.

Avoidance:

- Weight change in OI above static OI.
- Reduce options-chain weight in the last 2 days before expiry.

## 31. Layer 2 Runtime Rules: Sector Selection

Layer 2 runs at 9:00 AM to 9:20 AM and continuously after the open.

Purpose:

- trade with the strongest sector tide
- avoid strong-looking stocks inside weak sectors
- map macro and event drivers to stock selection

Rules:

- Long candidates should come from top 2 to 3 performing sectors.
- Short candidates should come from bottom 2 to 3 sectors.
- If no sector stands out, reduce activity.
- Sector relative strength versus Nifty must affect the stock score.
- Sector weakness can be overridden only by a strong stock-specific event.

### 31.1 Pre-Market Sector Driver Map

| Overnight Signal | Sector Impact |
| --- | --- |
| US tech rally | Indian IT positive |
| crude spike | OMCs, paints, airlines negative; ONGC positive |
| weak INR | IT positive; import-heavy auto/API companies negative |
| RBI rate-cut expectation | banking, realty, NBFC positive |
| China weakness | metals negative; China+1 manufacturing can benefit |
| global risk-off | pharma/FMCG defensive; small/midcaps weaker |
| gold rally | Titan, Muthoot, Manappuram positive |
| strong FII buying | large-cap banking and IT positive |
| government capex | infra, defense, railways positive |

### 31.2 Sector Rotation Framework

| Phase | Leaders | Laggards | Rule |
| --- | --- | --- | --- |
| Early bull | banking, NBFC, realty | FMCG, pharma | buy recovery leaders |
| Mid bull | IT, auto, capital goods | utilities, defensives | ride earnings acceleration |
| Late bull | metals, commodities, smallcaps | few clear laggards | reduce aggression, watch euphoria |
| Early bear | FMCG, pharma, sometimes IT | realty, smallcaps, NBFC | shift defensive |
| Deep bear | cash, gold, government bonds | most equities | survival mode |

Failure modes:

- One heavyweight can distort a sector index.
- Stock-specific fraud, large orders, or result surprise can override sector context.

## 32. Layer 3 Runtime Rules: Stock Universe Filtering

Layer 3 runs the evening before and updates live.

Purpose:

- remove unsafe stocks before any setup logic
- prevent liquidity traps, circuit traps, and manipulated micro-cap trades

### 32.1 Hard Filter Thresholds

| Filter | Intraday Default | Swing Default |
| --- | ---: | ---: |
| F&O stock list | required for shorting | preferred |
| average daily turnover | > INR 50 crore | > INR 20 crore |
| bid-ask spread | < 0.10 percent large-cap | < 0.25 percent |
| F&O ban | reject | reject if derivative-dependent |
| ASM/GSM | reject | reject |
| corporate action today | reject or block until adjusted | reject or block until adjusted |
| circuit limit proximity | avoid | avoid unless planned |
| market cap | > INR 5,000 crore | > INR 2,000 crore |
| free float | > 30 percent | > 25 percent |
| price floor | > INR 100 | > INR 50 |

### 32.2 Delivery Percentage Rules

Delivery percentage is one of the strongest NSE-specific sponsor clues.

| Delivery Percent | Interpretation |
| --- | --- |
| < 20 percent | mostly speculative or intraday |
| 20 to 40 percent | normal/moderate conviction |
| 40 to 60 percent | above average; institutions likely involved |
| > 60 percent | very high conviction delivery activity |

Delivery anomaly matrix:

| Price/Volume/Delivery Pattern | Meaning | Action |
| --- | --- | --- |
| price up + volume up + delivery > 50 percent | accumulation | long candidate |
| price up + volume up + delivery < 25 percent | speculative pump risk | avoid or downgrade |
| price down + volume up + delivery > 50 percent | institutional distribution | exit longs or short candidate |
| price down + volume up + delivery < 25 percent | panic retail selling | contrarian watchlist only |

Failure mode:

- Delivery data is T+1 and does not directly identify buyer versus seller.

Avoidance:

- Combine delivery with bulk/block deals, promoter/MF/FII data, and price reaction.

### 32.3 Institutional Activity Rules

Track:

- FII/DII daily cash and derivative data.
- Bulk deals above 0.5 percent of equity.
- Block deals.
- SEBI SAST disclosures.
- Insider/promoter/KMP trades.
- Mutual fund monthly portfolio changes.
- FPI stock-wise data.
- Promoter holding changes.
- Pledged shares.

Hard-block or major downgrade:

- Promoter pledge above 50 percent.
- Promoter selling above 2 percent in a quarter without clear reason.
- FPI holding dropping for 3 or more consecutive quarters.
- MF holding dropping while price rises.
- Unknown bulk deal at unusual price with related-party risk.

High-conviction signals:

- promoter open-market buying
- multiple mutual funds adding the same stock
- FII and DII both increasing holding
- large block deal at premium to market price

### 32.4 Government And Policy Signal Rules

Use policy, not politician personal trades.

Useful India-specific sources:

- Union Budget themes.
- PLI scheme beneficiaries.
- defense order recipients.
- PSU bank recapitalization.
- DIPAM and government shareholding changes.
- SEBI and RBI regulation changes.

Rule:

Policy can create multi-month sector trends, but announced news may already be priced in. Score it as CAUSE only when the revenue or flow impact is still actionable.

## 33. Layer 4 Runtime Rules: Setup Identification

Layer 4 runs only after Layers 0 to 3 allow the stock to proceed.

Purpose:

- choose the actual setup type
- separate intraday and swing logic
- avoid treating every bullish chart as the same trade

### 33.1 Intraday Setup: Gap And Go

Long setup:

- gap above previous close greater than 2 percent
- pre-open volume greater than 3x normal pre-open
- strong catalyst
- GIFT Nifty and Nifty aligned green
- sector green and outperforming
- first 5-minute candle closes in upper 60 percent of range

Short setup:

- gap below previous close greater than 2 percent
- pre-open volume greater than 3x normal pre-open
- strong negative catalyst
- GIFT Nifty and Nifty aligned red
- sector red and underperforming
- first 5-minute candle closes in lower 60 percent of range

Entry:

- long above first 15-minute high
- short below first 15-minute low

Stop:

- long below first 15-minute low
- short above first 15-minute high

Minimum target:

- 2:1 reward-to-risk or next major level

Failure modes:

- gap without catalyst usually fills
- gap against market direction fails often
- gap into major resistance rejects
- pre-open volume without first-15-minute follow-through traps traders

### 33.2 Intraday Setup: Opening Range Breakout

Parameters:

- opening range: first 15 minutes aggressive, first 30 minutes conservative
- breakout candle volume above 1.5x opening-range volume
- Nifty aligned in same direction
- price above VWAP for longs and below VWAP for shorts
- ADX above 20

Reject ORB when:

- ADX below 20 and range-bound day likely
- opening range is wider than 1.5 percent of stock price
- opening range is narrower than 0.3 percent of stock price
- price whipsaws through range multiple times

### 33.3 Intraday Setup: VWAP Reclaim Or Rejection

Rules:

- price drops to VWAP and bounces with volume = possible institutional long support
- price rallies to VWAP and rejects with volume = possible institutional selling
- price crosses VWAP repeatedly = no conviction, avoid

### 33.4 Intraday Setup: Relative Strength

Rule:

If Nifty is down but a stock is flat or green, and the sector is aligned, the stock has relative strength.

Screener condition:

- stock percent change exceeds Nifty percent change by at least 0.5 percent in first 30 minutes
- sector confirms

Entry:

- wait for Nifty stabilization or recovery trigger

### 33.5 Swing Setup: VCP

Parameters:

- prior uptrend greater than 30 percent over last 3 to 6 months
- 3 to 4 contractions, each smaller than previous
- volume below 50-day average inside base
- Bollinger Band width near multi-week low
- breakout volume above 150 percent of average
- price within 25 percent of 52-week high

Failure modes:

- VCP in weak market or weak sector
- low breakout volume
- breakout directly into overhead supply

### 33.6 Swing Setup: 21 EMA Pullback

Parameters:

- price > 50 DMA > 200 DMA
- pullback touches or approaches 21 EMA
- pullback volume below average
- bounce candle has above-average volume
- RSI in 40 to 55 zone during pullback

### 33.7 Swing Setup: Sound Base Breakout

Parameters:

- base duration 4 to 12 weeks
- base depth less than 20 percent
- prior uptrend above 25 percent
- volume quiet inside base
- breakout volume above 200 percent of average
- measured target = base depth added to breakout point

### 33.8 Swing Setup: PEAD

Post-Earnings Announcement Drift is allowed only when event risk is the actual strategy.

Parameters:

- EPS beat above 15 percent or revenue beat above 10 percent
- result-day gap above 3 percent
- result-day volume above 300 percent of average
- price holds upper 50 percent of gap candle for 3 to 5 days
- sector is not in downtrend

Reason:

Institutions often cannot buy full size in one day, so strong result winners may drift as accumulation continues.

### 33.9 Swing Setup: True Relative Strength

Parameters:

- Nifty down 1 to 3 percent in the last week
- stock flat or making new 20-day high
- sector not hostile

Interpretation:

Institutional accumulation is defying market weakness.

Entry:

- wait for market stabilization or bounce.

## 34. Layer 5 Runtime Rules: Confirmation And Multi-Factor Edge

Layer 5 runs after setup identification and before entry.

Purpose:

- convert a setup hypothesis into a trade candidate
- detect traps before capital is exposed

### 34.1 Multi-Timeframe Alignment

| Timeframe | Use |
| --- | --- |
| monthly | major trend; must not be downtrend for swing longs |
| weekly | swing direction and resistance check |
| daily | primary swing setup |
| 4H/1H | entry refinement |
| 15-minute | intraday momentum and ORB/VWAP context |
| 5-minute | precise execution |

Rule:

A daily breakout with weekly resistance immediately above is high failure risk. A daily breakout with weekly support below and monthly uptrend is higher quality.

### 34.2 Volume And OI Confirmation Matrix

| Price Action | Volume | OI | Meaning |
| --- | --- | --- | --- |
| breakout up | > 200 percent average | increasing | strong long confirmation |
| breakout up | normal/low | flat | fake breakout risk |
| breakout up | > 200 percent average | decreasing | short-covering rally, may not sustain |
| pullback to support | decreasing | increasing | healthy pullback |
| pullback to support | increasing | decreasing | longs exiting |
| support breakdown | > 200 percent average | increasing | breakdown confirmed |
| support breakdown | normal/low | flat | shakeout or bear trap risk |

### 34.3 RVOL By Time Of Day

Formula:

`RVOL-TOD = volume so far today / average volume by same time over last 20 sessions`

Rules:

| Time IST | RVOL-TOD > 2.0 | RVOL-TOD < 0.5 |
| --- | --- | --- |
| 9:15 to 9:45 | significant early activity | avoid dead stock |
| 10:00 to 11:00 | confirms momentum | fading momentum |
| 11:00 to 1:00 | unusual lunch activity | normal quiet period |
| 1:00 to 2:30 | institutions active | normal |
| 2:30 to 3:30 | strong close likely | weak close likely |

### 34.4 Stock Options Confirmation

For F&O stocks:

| Signal | Bullish | Bearish |
| --- | --- | --- |
| unusual call volume | call volume > 3x OI | not applicable |
| unusual put volume | not applicable | put volume > 3x OI |
| IV rank | low IV rank < 30 percent supports option buying | high IV rank > 70 percent favors caution/selling |
| price + OI | price up + OI up = long build-up | price down + OI up = short build-up |
| stock PCR | > 1.0 can indicate support | < 0.5 can indicate resistance |

### 34.5 Trap Detection

Trap rules:

| Trap | Detection | Avoidance |
| --- | --- | --- |
| bull trap | breaks resistance then reverses with upper wick | require close above level and 2+ candle hold |
| bear trap | breaks support then reverses with lower wick | require close below level and check OI |
| VWAP rejection | breakout cannot sustain above VWAP | downgrade or reject |
| volume without progress | huge volume but tiny price movement | absorption; avoid breakout |
| breakout against index | stock breaks out while Nifty falls | wait for index alignment |
| breakout into supply | breakout enters prior distribution zone | check volume profile/supply zone |

## 35. Layer 6 Runtime Rules: Risk Engine And Position Sizing

Layer 6 runs before any order.

Purpose:

- decide whether the trade can be taken with controlled loss
- size exposure according to edge, volatility, liquidity, and account risk

### 35.1 Stop-Loss Methods

| Method | Rule | Best For |
| --- | --- | --- |
| ATR | stop = entry - 1.5x ATR for longs | universal volatility-adjusted |
| structure | below swing low or above swing high | price-action setups |
| VWAP | below VWAP for intraday longs | intraday |
| moving average | below 20 EMA intraday or 50 DMA swing | trend following |

Hard rules:

- never risk more than 1 percent of account on intraday trades
- never risk more than 2 percent of account on swing trades
- never move stop in the wrong direction
- never allow total open risk above 5 percent of account
- trail stops after trade moves 1R in favor

### 35.2 Position Sizing Formula

Formula:

`position_size_shares = (account_size * risk_per_trade_percent) / abs(entry_price - stop_price)`

Setup-quality multiplier:

| Setup Score | Size Multiplier |
| --- | ---: |
| 14 to 16 out of 16 | 1.00x |
| 11 to 13 out of 16 | 0.75x |
| 8 to 10 out of 16 | 0.50x |
| below 8 out of 16 | no trade |

### 35.3 Secondary 16-Point Setup Score

The original 28-point CAUSE/SPONSOR/STRUCTURE/FLOW score remains the causal score.

The 16-point score is an execution-quality score before entry.

| Factor | Points |
| --- | ---: |
| market regime bullish/aligned | 2 |
| sector outperforming | 2 |
| stock above 20/50/200 EMA for longs | 2 |
| RVOL-TOD > 2 | 2 |
| clean catalyst | 2 |
| tight spread below 0.1 percent | 1 |
| breakout near 52-week high | 1 |
| options OI structure favorable | 1 |
| risk-reward above 2:1 | 2 |
| no event risk in next 5 sessions | 1 |

Rules:

- full-size trade requires score >= 12 out of 16
- score below 8 is no-trade
- this score cannot override a hard fail from earlier layers

### 35.4 Expectancy Rule

Expectancy formula:

`expectancy = (win_rate * average_win) - (loss_rate * average_loss)`

Rules:

- win rate alone is meaningless
- a 40 percent win-rate strategy with 3:1 reward-to-risk can be better than 70 percent win rate with 0.5:1 reward-to-risk
- every setup type must be journaled and later validated by expectancy

Reference assumptions until validated:

| Strategy | Typical Win Rate | Average Win:Loss |
| --- | ---: | ---: |
| filtered gap-and-go | 55 percent | 2:1 |
| filtered ORB | 45 percent | 2.5:1 |
| VCP breakout | 50 percent | 3:1 |
| 21 EMA pullback | 55 percent | 2:1 |
| random breakout without filters | 35 percent | 1.5:1 and negative expectancy |

## 36. Layer 7 Runtime Rules: Execution And Order Management

Layer 7 runs at the moment of entry.

Purpose:

- prevent a good idea from becoming a bad trade because of poor fills
- choose the right order type and timing window

### 36.1 Order-Type Rules

| Order Type | Use | Risk |
| --- | --- | --- |
| limit | need exact price | may miss fast move |
| market | speed matters | slippage |
| SL-M | stop becomes market order | bad fill possible in gap |
| SL-L | stop with limit | may not execute if price gaps past limit |
| bracket | entry + stop + target | broker support varies |
| cover | intraday discipline with mandatory stop | less flexible |

### 36.2 Execution Timing Rules

| Time IST | Character | Rule |
| --- | --- | --- |
| 9:15 to 9:30 | high volatility, wide spreads | observe; build ORB/gap setup, do not chase |
| 9:30 to 10:00 | ORB triggers, VWAP establishes | valid entry window |
| 10:00 to 11:30 | trend clearer | best momentum window |
| 11:30 to 1:00 | lunch chop | avoid most new entries |
| 1:00 to 2:30 | institutions resume | trend resumption possible |
| 2:30 to 3:15 | last-hour push/squaring | manage exits or swing timing |
| 3:15 to 3:30 | closing mechanics | exit intraday positions |

### 36.3 Slippage Rules

Reference slippage:

| Category | Expected Slippage |
| --- | ---: |
| Nifty 50 | 0.02 to 0.05 percent |
| Nifty Next 50 | 0.05 to 0.10 percent |
| Midcap 150 | 0.10 to 0.25 percent |
| Smallcap | 0.25 to 1.00 percent |

Hard rule:

If estimated slippage is more than 20 percent of stop distance, the position is too large or the stock is not liquid enough.

## 37. Layer 8 Runtime Rules: Post-Entry Monitoring And Exit

Layer 8 runs after a position is live.

Purpose:

- manage risk after entry
- avoid emotional override
- turn outcomes into calibration data

### 37.1 Trailing Stop Rules

| Method | Rule |
| --- | --- |
| fixed R | move stop to breakeven at 1R |
| Chandelier | trail by 2x ATR from highest high |
| moving average | exit below 8 EMA intraday or 21 EMA swing |
| time stop | exit if no progress after 30 minutes intraday or 5 days swing |
| partial profit | book 50 percent at 1R and trail rest |

### 37.2 Add Or Exit Rules

| Condition | Action |
| --- | --- |
| trade in favor + volume rising + sector strong | consider pyramiding at 1R |
| trade stalls near target + volume declines | book partial |
| VIX spikes or breadth collapses | tighten all stops |
| stock enters F&O ban | exit derivative positions |
| news event approaches | exit or hedge |

### 37.3 End-Of-Day Review Rules

Log:

- setup-quality score
- entry timing
- stop placement quality
- target behavior
- market-regime accuracy
- sector-call accuracy
- emotional state
- rule violations

## 38. Daily Workflow Rules

### 38.1 Evening Before: 7:00 PM To 10:00 PM IST

Checklist:

- check US market close: S&P 500, Nasdaq, VIX
- check crude, gold, USD/INR, DXY
- download FII/DII daily data
- check bulk and block deals
- review corporate announcements
- check next-day event calendar
- check F&O ban list
- run swing screener on daily data
- prepare preliminary 5 to 10 stock watchlist

### 38.2 Early Morning: 6:00 AM To 9:00 AM IST

Checklist:

- check GIFT Nifty
- check Asian markets
- check US futures
- determine market bias: bullish, bearish, or neutral
- review Nifty options chain
- classify watchlist into long and short candidates
- set price alerts

### 38.3 Pre-Open: 9:00 AM To 9:15 AM IST

Checklist:

- monitor pre-open prices
- identify gap-up and gap-down stocks
- cross-check each gap with catalyst
- calculate reward-to-risk from pre-open levels
- finalize 3 to 5 active trading candidates
- prepare bracket, stop, or alert orders if allowed

### 38.4 Market Open: 9:15 AM To 9:45 AM IST

Checklist:

- observe first 5 minutes
- do not trade in first 2 minutes by default
- mark 15-minute opening range
- check live sector leaders and laggards
- check advance/decline ratio
- verify VWAP direction
- execute only if ORB or gap-and-go confirms

## 39. Meta-Failure Mode Rules

TrendForge must explicitly detect and survive whole-system failure modes.

| Failure | Detection | Survival Rule |
| --- | --- | --- |
| black swan | cannot predict | position sizing and max portfolio risk cap |
| liquidity crisis | spreads widen, depth vanishes, circuits hit | use limit orders, cut size immediately |
| correlation breakdown | all positions move together | hedge or flatten exposure |
| strategy decay | monthly expectancy drops | recalibrate or disable strategy |
| overfitting | strong backtest, weak live result | walk-forward and out-of-sample validation |
| data quality failure | anomalous or stale readings | multi-source verification and sanity checks |
| emotional override | stops moved, revenge trades, FOMO | journal and enforce rules |
| regulatory change | SEBI/broker/margin changes | cash buffer, no max margin |

## 40. Updated Acceptance Criteria After Merge

TrendForge is not ready for implementation unless the following are defined:

- exact runtime gate sequence
- global macro inputs and fallback behavior
- market regime classifier
- sector selection rules
- tradability filters and thresholds
- delivery and institutional activity rules
- setup definitions for intraday and swing
- confirmation rules for MTF, volume, OI, RVOL-TOD, options, and traps
- risk formula and account-risk defaults
- execution window rules
- post-entry monitoring rules
- daily workflow stages
- meta-failure detection
- no-trade and WAIT behavior

## 41. Updated Open Decisions

These decisions are still needed before coding:

1. Should the first implementation optimize for intraday, swing, or both with separate profiles?
2. Should the first usable version be CLI, backend API, or full dashboard?
3. Should F&O options-chain logic be active in v1 or stored as future rules?
4. What is the capital bracket: below INR 5L, INR 5L to 25L, INR 25L to 1Cr, or above INR 1Cr?
5. Which broker/data source is available first: Upstox, Angel One, Zerodha, paid feed, or public NSE-only?
6. Should alerts be dashboard-only first or Telegram from v1?
7. Should auto-order hooks be completely excluded from v1, or only designed as disabled placeholders?

## 42. Verified Merge From Complete Build Bible

The Complete Build Bible attachment was verified across all 503 lines before this section was added.

This merge adds the deeper institutional-radar rules that were either missing or only partially defined in the earlier plan.

### 42.1 Four Root Causes Of A Trend

TrendForge must classify each candidate by the root cause of the move, because each cause has different run behavior and exit behavior.

| Cause Type | Meaning | Footprint | Strategy Bias |
| --- | --- | --- | --- |
| information asymmetry | someone informed acts before the market fully knows | promoter buying, SAST, bulk deal, Wyckoff absorption, unusual options before catalyst | swing accumulation; highest early edge |
| forced or mandatory flow | an actor must buy/sell regardless of opinion | index inclusion/exclusion, SIP deployment, margin calls, short squeeze, gamma squeeze, expiry pinning | explosive but must manage exit fast |
| fundamental re-rating | future cash flows are repriced | earnings beat, guidance raise, order book expansion, margin improvement, PLI tailwind, rating upgrade | PEAD or multi-week drift |
| reflexivity or feedback | the move feeds itself | CTA/trend following, short stops, gamma hedging, media/FOMO | profitable if early, dangerous if late |

Rule:

The CAUSE layer must not only say "catalyst present". It must label which of these four causes is active and choose setup/exit logic accordingly.

### 42.2 Master Trap Question

Every candidate must answer:

"Who is on the other side of this trade, and are they being forced to trade against the trend, or am I the fuel?"

Rules:

- If TrendForge can identify a forced counterparty, conviction can increase.
- If the trade relies only on voluntary buying with no forced counterparty, conviction must be lower.
- The WHY output must include counterparty analysis when available.
- If the system cannot name who is trapped, squeezed, underweight, rebalancing, or accumulating, it must say so.

### 42.3 Six Actor Classes To Track

The SPONSOR layer must classify sponsor evidence by actor type.

| Actor | Role | Tracking Method | Key Read |
| --- | --- | --- | --- |
| FII | marginal foreign flow driver | NSE FII cash/F&O, index futures long/short, NSDL/FPI holdings | rate of change matters more than level |
| DII | domestic mutual fund/insurance/pension flow | NSE DII, AMFI monthly holdings | can absorb FII selling; check passive vs conviction |
| promoter/insider | highest-information actor | SAST, insider disclosures, pledge filings | open-market buying is high signal; pledge/selling is risk |
| named super-investor | mid/smallcap sponsor | bulk/block deals, Trendlyne portfolios | named buyer can drive long trend |
| market maker/option writer | amplifier/pinner, not original cause | option chain, IV, GEX, gamma flip | long gamma dampens, short gamma amplifies |
| retail/operator | late money or fake trend creator | delivery %, ASM/GSM, low float, circuit pattern | low-quality pump risk |

Operator-pump hard reject:

- market cap below INR 2,000 crore
- delivery below 20 percent
- price rising sharply
- no real sponsor

### 42.4 Stronger Shortlist Gate

The final shortlist gate is now stricter:

1. Total causal score must be at least 18 out of about 28, configurable.
2. At least 3 of 4 layers must pass.
3. Minimum layer thresholds must pass: CAUSE >= 2, SPONSOR >= 4, STRUCTURE >= 2, FLOW >= 2.
4. Candidate must rank at or above the 90th percentile within today's universe.
5. All trap hard-gates must pass.

Reason:

A stock should not enter the radar only because it crossed a static score. It must also be strong relative to the current market universe.

### 42.5 Complete Data Architecture Rules

The first production data model must be point-in-time correct.

Required SQLite tables:

| Table | Purpose |
| --- | --- |
| stocks | master universe: symbol, ISIN, name, sector, market cap, free float, F&O flag, listing date |
| price_daily | adjusted OHLC, volume, traded value, delivery quantity, delivery percent, adjustment factor |
| price_intraday | 1-minute candles for intraday and backtest |
| fii_dii_daily | cash/futures/options flow by entity and segment |
| bulk_deals | buyer/seller names, quantity, value, bulk/block type |
| options_chain | expiry, strike, CE/PE, OI, change OI, volume, IV, LTP, delta, gamma, theta, vega |
| corporate_actions | splits, bonuses, dividends, adjustment status |
| promoter_activity | buy/sell/pledge/release, person, quantity, value, post-holding |
| mf_holdings | monthly scheme holdings and change from previous month |
| news_events | source, headline, catalyst type, sentiment score |
| trades | journal with setup, score, entry/exit, P&L, R multiple, regime, notes |

Corporate-action rule:

- Price history must be adjusted during ingestion, not lazily during chart/query rendering.
- Missing split/bonus/dividend adjustment is a data-integrity failure.

### 42.6 Data Health State Rules

Every data source must maintain:

- source name
- last success time
- consecutive failures
- status: GREEN, AMBER, or RED

State rules:

| State | Meaning |
| --- | --- |
| GREEN | last success under 1 hour and zero consecutive failures |
| AMBER | last success 1 to 6 hours ago or 1 to 2 consecutive failures |
| RED | last success above 6 hours or 3+ consecutive failures |

Critical rule:

If a critical source goes RED, the affected layer must degrade visibly and notify the user. It must never silently score with broken data.

### 42.7 Source Claims That Need Live Verification Before Build

The Build Bible includes specific broker/API/regulatory claims. These must be treated as source-document assumptions until checked against official docs during implementation.

Must verify before coding live integrations:

- Upstox current rate limits.
- Upstox WebSocket instrument caps and Greek availability.
- Angel SmartAPI current endpoints and limits.
- NSE endpoint paths and current anti-bot behavior.
- SEBI/broker rules for automated order placement.

Until verified, TrendForge remains read-only plus alerts. No auto-order execution.

### 42.8 Precise Staleness Decay Rules

Sponsor signals must decay by signal type.

Formula:

`weight = exp(-lambda * age_days)`

Default lambda values:

| Signal | Lambda | Meaning |
| --- | ---: | --- |
| delivery percent | 0.15 | fast decay, about 5-day half-life |
| promoter buy | 0.04 | slower decay, about 17-day half-life |
| bulk deal | 0.07 | about 10-day half-life |
| mutual fund holding | starts at 0.4 weight | delayed by nature, never starts full weight |

Rule:

Stale data can support context, but stale data cannot create high conviction by itself.

### 42.9 Wyckoff Effort-Vs-Result Algorithm

For each of the last 20 daily candles:

- `effort = volume / 20_day_average_volume`
- `result = abs(close - open) / ATR`

Absorption bar condition:

- effort > 1.5
- result < 0.5

If at least 3 absorption bars exist in the last 20 sessions, add Sponsor evidence.

Reason:

Large volume with small price movement means supply may be absorbed quietly. This is a big-player accumulation footprint that normal price indicators miss.

### 42.10 VCP Detection Algorithm

VCP detection must require:

1. prior uptrend above 30 percent in last 3 to 6 months
2. consolidation over about 3 to 4 weeks or more
3. each contraction range smaller than prior contraction
4. volume below 50-day average during base
5. Bollinger Band width near multi-week low
6. breakout volume above threshold

This prevents labeling any sideways chart as VCP.

### 42.11 True Relative Strength Formula

True relative strength is not RSI.

Formula:

`RS_ratio = stock_return(period) / nifty_return(period)`

High-quality condition:

- Nifty down 1 to 3 percent in the last week
- stock flat or making new 20-day high

Meaning:

The stock is being accumulated while the market is weak. When the index recovers, this stock can lead.

### 42.12 GEX And Gamma Flip Rules

For each option strike:

`gex_strike = gamma * open_interest * contract_size * spot^2 * 0.01`

Directional handling:

- calls contribute positive dealer gamma when dealers are long calls
- puts require negative adjustment when dealer positioning implies short-gamma exposure
- exact sign assumptions must be documented during implementation

Gamma flip:

- the spot level where total GEX crosses zero

Interpretation:

| State | Behavior |
| --- | --- |
| positive GEX / spot above flip | dealers dampen moves, range or pin behavior more likely |
| negative GEX / spot below flip | dealers amplify moves, trend or squeeze behavior more likely |

Rule:

Gamma/GEX improves FLOW and trap detection. It cannot replace CAUSE and SPONSOR evidence.

### 42.13 Cross-Market Driver Alignment

Each stock must map to its relevant external driver where possible.

| Stock Group | Driver |
| --- | --- |
| metals | LME copper/iron ore plus DXY |
| IT | Nasdaq plus USD/INR |
| pharma | US FDA news plus USD |
| paints | Brent crude inverse risk |
| OMCs | Brent crude inverse risk |
| gold financiers | gold price |

Rule:

A breakout gets driver-confirmation credit only when the mapped driver supports the same direction as the trade.

Example:

Tata Steel breakout plus copper rising plus DXY falling = stronger than Tata Steel breakout alone.

### 42.14 Independence Matrix Penalty Formula

Known overlapping pairs:

- FLOW RVOL-TOD and STRUCTURE breakout volume both use volume
- FLOW options OI and CAUSE gamma/reflexivity both use OI
- SPONSOR delivery percent and FLOW volume both share volume-related evidence

Penalty rule:

`penalty = 0.3 * min(signal_A_points, signal_B_points)`

Reason:

The same evidence must not be counted twice as if it were independent confirmation.

### 42.15 Trap Hard-Gates

These cannot be overridden by score.

| Gate | Reject Condition |
| --- | --- |
| close above/below level | level only touched, not closed through |
| 2-candle hold | breakout fails to hold for at least 2 candles |
| upper wick | long upper wick over 40 percent of range on high volume for longs |
| VWAP | long is below VWAP or VWAP slope is flat/falling |
| index alignment | long breakout while Nifty is falling, unless explicitly relative-strength setup |
| HVN/supply | breakout runs directly into prior high-volume node or supply zone |

### 42.16 Eleven Trap Types

TrendForge must classify trap warnings, not only reject generically.

| Trap | Detection |
| --- | --- |
| operator pump | low market cap, low delivery, price spike, no sponsor |
| short squeeze | high short fuel, RVOL spike, weak fundamental sponsor |
| gamma squeeze | exploding call OI/GEX, unsustainable after gamma flip |
| index-inclusion front-run | run-up before inclusion, dump risk after event |
| earnings gap fade | gap with delivery below 25 percent |
| news priced in | catalyst public for more than 2 sessions and stock already up 15 percent or more |
| pledged-share mask | high pledge or promoter selling despite price strength |
| narrow-index divergence | index green, internal breadth weak |
| breakout into supply | breakout directly into HVN/distribution zone |
| liquidity mirage | large percent move on thin traded value |
| failed reclaim | level breaks, pulls back, then cannot reclaim |

### 42.17 Reasoning Generator Required Clauses

The WHY output must be assembled from evidence, not generic text.

Required clause types:

- catalyst clause
- sponsor clause
- delivery clause
- MF/promoter/bulk-deal clause when present
- setup clause
- RVOL/OI/options clause
- counterparty analysis clause
- risk clause with entry, stop, target, R:R, and size
- source and date for every numeric claim

### 42.18 Regime-Scaled Risk Formula

Base risk defaults:

- intraday: 0.5 percent
- swing: 1 percent

Regime multiplier:

| Regime | Multiplier |
| --- | ---: |
| strong uptrend and VIX < 15 | 1.2x |
| mild uptrend | 1.0x |
| range-bound | 0.7x |
| downtrend | 0.5x or 0x |
| crash | 0x |

Score multiplier:

| Causal Score | Multiplier |
| --- | ---: |
| 22 to 28 | 1.0x |
| 18 to 21 | 0.75x |
| 15 to 17 | 0.5x |
| below 15 | no trade |

Half-Kelly rule:

`kelly_fraction = (win_probability * average_win_loss_ratio - loss_probability) / average_win_loss_ratio`

Use half-Kelly for safety and clamp final account risk between 0.2 percent and 1.5 percent.

Final formula:

`risk_per_trade = base_risk * regime_multiplier * score_multiplier * half_kelly_adjustment`

### 42.19 Portfolio Correlation Rules

For every new candidate:

- compare against open positions using 60-day daily return correlation
- if correlation > 0.7, flag as same bet and reduce size
- cap per-sector exposure at 30 percent of portfolio risk
- cap total open risk at 5 percent of account

Reason:

Five banking longs are one banking bet, not five independent trades.

### 42.20 Exit Engine Enhancements

Exit types:

1. Chandelier trailing stop: highest high minus 2x ATR.
2. Moving-average trail: 8 EMA for intraday, 21 EMA for swing.
3. Time stop: no progress after 30 minutes intraday or 5 days swing.
4. Regime kill switch: India VIX spikes more than 30 percent in one session.
5. Breadth kill switch: advance/decline worse than 1:3.
6. F&O ban on held derivative stock: exit derivative positions.
7. Profit ladder: book 50 percent at 1R, 25 percent at 2R, trail final 25 percent.
8. Target hit: measured move or predefined R:R level.

### 42.21 Options Depth Rules

Beyond basic OI, TrendForge must track:

| Feature | Meaning |
| --- | --- |
| IV term structure | near-month vs far-month IV; inversion can imply future event risk |
| IV skew/risk reversal | 25-delta call IV minus 25-delta put IV; extremes can warn of crowding |
| 0DTE/expiry dynamics | gamma dominates expiry day; max-pain pinning stronger unless catalyst breaks it |
| premium concentration | large premium at one strike can imply informed money; scattered small trades imply retail noise |

Rule:

Options depth belongs in confirmation and trap detection. It does not create a standalone trade without the causal layers.

### 42.22 Build Modules Added By Build Bible

The file-by-file plan adds or clarifies these modules:

| Module | Purpose |
| --- | --- |
| backend/adapters/cross_market.py | external driver feeds and mapping |
| backend/engine/intraday_microstructure.py | wick, VWAP, HVN, reclaim, liquidity-mirage checks |
| backend/engine/swing_extras.py | credit rating, PEAD, longer-horizon swing extras |
| backend/engine/options_depth.py | IV skew, term structure, 0DTE, premium concentration |
| backend/engine/event_preposition.py | expected-move/event positioning logic |
| backend/engine/crowding.py | crowded positioning and exhaustion risk |
| backend/engine/shorting_asymmetry.py | borrow/lendability and short feasibility |
| backend/engine/relative_rank.py | top-decile universe ranking |

### 42.23 Funnel Telemetry Conflict Resolution

The Build Bible says funnel telemetry can auto-loosen or auto-tighten thresholds to keep 3 to 8 picks.

This conflicts with the earlier rule that TrendForge must not silently relax filters.

Final rule:

- Funnel telemetry may recommend threshold changes.
- It may show why the funnel produced 0 or 50 candidates.
- It may support a named profile such as strict, normal, or exploratory.
- It must never silently loosen thresholds inside the main actionable mode.
- If thresholds change, the UI must label the active profile and show what changed.

### 42.24 Testing Additions

Required unit tests:

- VCP positive and negative examples
- staleness decay decreases with age
- independence penalty applies to correlated evidence
- slippage rejects above 20 percent of stop distance
- each trap hard-gate independently
- reasoning generator contains expected evidence and source/date
- position sizing math including regime and half-Kelly clamp

Required integration tests:

- fetch to store to score to output
- source fallback chain behavior
- point-in-time backtest correctness
- source RED state degrades affected layer visibly

### 42.25 Radar Improvement Summary

These additions improve the scanning radar by moving it from "find stocks moving" to "find stocks with fuel, sponsor, setup, confirmation, and survivable risk."

The important radar upgrades are:

- forced-counterparty detection
- actor classification
- top-decile relative ranking
- source health and staleness confidence
- gamma flip and GEX behavior
- IV skew, term structure, and premium concentration
- cross-market driver alignment
- hard trap taxonomy
- half-Kelly and regime-scaled sizing
- portfolio correlation awareness
- funnel telemetry with visible threshold governance

## 43. Hybrid Dashboard Experience And Output Plan

This section adds the user-facing experience layer on top of the existing TrendForge rules.

No previous rule is removed by this section. The existing causal engine, Layer 0 to Layer 8 pipeline, Build Bible additions, risk rules, data schema, GEX/options rules, trap rules, and no-auto-order rule remain active.

### 43.1 Product Shape

TrendForge should be built as a local command-center web dashboard:

- local Python/FastAPI backend
- SQLite database
- browser dashboard
- read-only market data and alerts
- no automatic order placement in v1

Reason:

- a single HTML file is too weak for live data, alerts, options, source health, journaling, and database history
- a terminal script is not visual enough for fast market decisions
- a full cloud app is premature and adds credential/security complexity
- a local web app is powerful, private, visual, and safer for the first build

### 43.2 Daily Screen Flow

The dashboard must guide the user through the market day instead of forcing the user to remember every check.

Required screens:

1. Evening Prep: 7:00 PM to 10:00 PM.
2. Morning Brief: 6:00 AM to 9:00 AM.
3. Pre-Open Scanner: 9:00 AM to 9:15 AM.
4. Live Radar: 9:15 AM onward.
5. Stock Deep Dive: opened from any candidate.
6. Position Size Calculator: before manual execution.
7. Trade Monitor: after entry.
8. Journal And Learning: after market close.

### 43.3 Output States

Every stock must show one clear state:

| State | Meaning | User Action |
| --- | --- | --- |
| READY | all required gates passed and entry trigger is active | may place trade manually after size check |
| WAIT | stock is good but confirmation or trigger is missing | watch only |
| REJECT | hard gate, trap, stale data, or risk failure | do not trade |
| NO_TRADE | market/day has no clean edge | preserve capital |

The system must never output only BUY or SELL.

### 43.4 Evening Prep Screen

Purpose:

- prepare tomorrow's bias before the market opens
- find event risk, bulk/block clues, sponsor activity, and swing candidates
- remove stocks that should not be touched tomorrow

Screen must show:

- US market close: S&P 500, Nasdaq, Dow, US VIX
- intermarket: crude, gold, USD/INR, DXY
- FII/DII: today, 5-day, and 20-day flow
- tomorrow's key events: results, RBI/SEBI events, F&O ban, ex-dividend
- bulk/block deals: buyer/seller name, price premium/discount, interpretation
- preliminary market bias
- suggested focus sectors
- warning list

Example output:

```text
EVENING PREP
US: S&P +0.8% | Nasdaq +1.2% | US VIX 14.2 low fear
Intermarket: Crude -1.2% | Gold +0.3% | USD/INR stable | DXY -0.2%
FII/DII: FII +8,900 Cr 5D | DII +4,200 Cr 5D
Events: TCS results tomorrow | RBI minutes 11:30 AM | F&O ban: IDFCFIRSTB, MANAPPURAM
Bulk/Block: TATAMOTORS block deal at premium by named institution
Verdict: BULLISH for tomorrow
Focus: IT and Banking
Caution: event stocks blocked for swing entries
```

### 43.5 Morning Brief Screen

Purpose:

- confirm or reject evening bias
- decide market regime and allowed strategy family
- tell the user where to focus before pre-open

Screen must show:

- GIFT Nifty and expected gap
- Asian markets
- US futures
- Nifty options chain snapshot
- PCR, max pain, call wall, put wall, OI trend
- FII futures long/short ratio
- regime classification
- support/resistance range
- sector expectations with reasons

Example output:

```text
MORNING BRIEF
GIFT Nifty: +0.65%, expected gap up 150-170 points
Asia: Nikkei green | Hang Seng green | Shanghai flat/weak
US Futures: confirming overnight strength

Nifty Options:
PCR 1.15 bullish | Max Pain 24,500 | Call Wall 25,000 | Put Wall 24,500
OI Trend: put writers defending lower strikes
FII Futures L/S: 0.72 bullish

Regime: STRONG UPTREND
Strategy: long breakouts allowed; avoid casual shorts
Sector Plan: IT BUY, Banking BUY, Metals WEAK, Pharma WAIT
```

### 43.6 Pre-Open Scanner Screen

Purpose:

- show early gap candidates
- separate real gaps from empty/speculative gaps
- produce watch candidates, not direct trades

Important rule:

Pre-open candidates are WATCH only. A stock cannot become READY until post-open confirmation passes.

Screen must show:

- gap-up stocks in target sectors
- gap-down stocks in weak sectors
- pre-open price
- gap percent
- catalyst quality
- event/corporate-action warnings
- empty-gap warnings
- mechanical-gap warnings such as ex-dividend

Example output:

```text
PRE-OPEN SCANNER
Gap Up:
INFY       +2.3% | Catalyst: Nasdaq/IT strength | VALID WATCH
ICICIBANK  +1.1% | Catalyst: FII banking flow   | WATCH
ADANIENT   +3.1% | Catalyst: none               | EMPTY GAP, AVOID

Gap Down:
TATASTEEL  -1.8% | Catalyst: China weakness     | SHORT WATCH

Warnings:
TCS result today: no swing trade
HDFCBANK ex-dividend: mechanical gap, do not short blindly
```

### 43.7 Live Radar Screen

Purpose:

- produce the main actionable radar
- show only stocks that are READY, WAIT, REJECT, or NO_TRADE with reasons
- keep the trader focused on the highest quality 3 to 8 candidates

Screen must show:

- live Nifty and Bank Nifty
- live breadth
- India VIX
- live sector heatmap
- funnel counts
- candidate cards with score, setup, state, entry, stop, target, and warning

Example output:

```text
LIVE RADAR 09:32
Nifty +0.58% | Breadth 2:1 | India VIX 13.2
Strong sectors: IT, Banking, Oil & Gas
Weak sectors: Metals, Realty

READY:
INFY | LONG | Score 23/28 + 14/16 | Gap&Go + ORB
Entry 1849 | Stop 1835 | T1 1870 | T2 1890
Why short: IT sector #1, RVOL-TOD 3.2x, VWAP hold, long OI build

WAIT:
ICICIBANK | LONG WATCH | Score 18/28 + 10/16
Reason: pulled back to VWAP; waiting for reclaim

REJECT:
ADANIENT | gap up but no catalyst; empty-gap risk
```

### 43.8 Stock Deep Dive Screen

Purpose:

- explain every decision so the user can verify the result
- show what passed, what failed, and what could still go wrong

Required sections:

- symbol, direction, setup, state, score, percentile
- Layer 0 to Layer 8 pass/fail chain
- 4-layer causal score: CAUSE, SPONSOR, STRUCTURE, FLOW
- 16-point execution score
- institutional activity
- forced-counterparty analysis
- options/GEX panel
- trap check
- event check
- data confidence
- exact evidence with source/date

Example output:

```text
INFY FULL ANALYSIS
State: READY LONG
Score: 23/28 causal | 14/16 execution | Percentile: Top 2%

Layer Chain:
Layer 0 Global: PASS
Layer 1 Regime: PASS
Layer 2 Sector: PASS
Layer 3 Tradable: PASS
Layer 4 Setup: PASS
Layer 5 Confirmation: PASS
Layer 6 Risk: PASS
Layer 7 Execution: waiting for user

4-Layer Score:
CAUSE: Nasdaq/IT driver and clean sector catalyst
SPONSOR: delivery 48%, FII sector buying, MF adding
STRUCTURE: above 20/50/200, breakout near high
FLOW: RVOL-TOD 3.2x, VWAP hold, OI long build-up

Counterparty:
Underweight/late buyers may be forced to chase IT strength.
No forced short squeeze detected.

Trap Check:
No upper wick, holds above VWAP, index aligned, not into supply.
```

### 43.9 Position Size Calculator

Purpose:

- prevent oversized trades
- convert a good idea into a controlled-risk plan

Screen must show:

- account size
- risk percent
- entry
- stop
- risk per share
- position size
- position value
- margin estimate if applicable
- target profit at T1/T2
- max loss
- slippage check
- sector exposure check
- same-bet correlation check
- margin/cash availability check

Example output:

```text
POSITION SIZE
Account: 10,00,000
Risk: 0.5% = 5,000
Entry: 1849
Stop: 1835
Risk/share: 14
Size: 357 shares
Max Loss: 4,998
Target 1: 1870 = 1.5R
Target 2: 1890 = 2.9R
Checks: risk OK, slippage OK, sector exposure OK, margin OK
```

### 43.10 Trade Monitor Screen

Purpose:

- help manage a manually placed trade
- show live context and exit actions

Screen must show:

- entry
- current price
- current P&L and R multiple
- stop
- target progress
- suggested trailing stop
- alerts
- live market and sector context
- warnings such as lunch hour, event timing, volume fade, VIX spike

Example output:

```text
ACTIVE TRADE: INFY LONG
Entry 1849 | Current 1862 | P&L +0.93R
Target 1 1870 | Target 2 1890
Alert: approaching T1
Alert: volume declining; momentum may stall
Action: book 50% at T1, move stop to breakeven
Context: IT still leading, VIX stable, breadth healthy
```

### 43.11 Journal And Learning Screen

Purpose:

- convert every result into calibration data
- show what worked and what failed
- improve future scoring only from evidence

Screen must show:

- daily P&L
- R multiple
- win/loss count
- per-trade notes
- what worked
- what failed
- whether system warnings were ignored
- market-bias accuracy
- sector-call accuracy
- setup score accuracy
- monthly expectancy
- best/worst setup and sector

Example output:

```text
JOURNAL
Trades: 2 | Wins: 1 | Losses: 1 | Net: +0.62R

INFY LONG: won because catalyst + sector + volume aligned.
TATASTEEL SHORT: lost because short was against bullish market.

System Accuracy:
Market bias correct
Sector call correct
Higher-scored trade won
Lesson: avoid shorts in strong bull unless exceptional conviction
```

### 43.12 Extra Panels To Add

The dashboard should also include:

- Why Rejected: shows strong-looking stocks rejected by hard gates
- WAIT Board: stocks close to trigger but not ready
- Data Confidence: source health per stock and per layer
- Forced Counterparty: who is trapped, squeezed, underweight, or forced
- Gamma/GEX Panel: squeeze versus pin behavior
- Breadth Danger Alarm: blocks breakouts during narrow-index rallies
- Threshold Profile: Strict, Normal, Exploratory; never silent auto-loosen
- Replay Mode: replay yesterday's market and decisions
- Watchlist Memory: tracks sponsor evidence building over days/weeks
- Stale Evidence Badge: stale data can support context but not high conviction

### 43.13 Final User Response Contract

Every actionable output must include:

- state: READY, WAIT, REJECT, or NO_TRADE
- direction
- setup
- causal score
- execution score
- percentile rank
- reason
- evidence
- entry trigger
- stop
- target
- position size
- trap warning
- exit plan
- data confidence

Minimum example:

```text
READY LONG: INFY
Reason: IT sector strongest, clean gap with catalyst, RVOL-TOD 3.2x, VWAP hold, delivery strong.
Entry: 1849 after 15-minute high break
Stop: 1835
Targets: 1870 / 1890
Size: 357 shares for 0.5% account risk
Trap Check: passed
Data Confidence: GREEN
```

### 43.14 Safety Boundary

TrendForge may recommend actions and alerts, but v1 must remain read-only.

Allowed:

- scan
- score
- explain
- alert
- calculate position size
- suggest stop movement
- journal

Not allowed in v1:

- automatic order placement
- hidden threshold relaxation
- claiming guaranteed prediction
- trading on stale or missing data without warning

## 44. Assessment Merge And Radar Upgrade Rules

This section merges the latest assessment into the existing plan.

No previous requirement is removed. The local web dashboard, FastAPI backend, SQLite storage, 8-screen flow, Layer 0 to Layer 8 gates, 4-layer causal engine, Build Bible rules, options/GEX rules, risk engine, journal, trap hard-gates, and no-auto-order boundary remain active.

The assessment does not replace the old plan. It tightens the radar so TrendForge can say:

- why a stock is eligible before market
- why a stock is confirmed live
- why a stock is rejected
- why a stock is only WAIT
- why the whole day is NO_TRADE
- which market mechanism is driving or blocking the trade

### 44.1 Architecture Lock

The correct first-build architecture remains:

```text
Local browser dashboard + FastAPI backend + SQLite database + read-only alerts
```

Reason:

- A single HTML file cannot support live data freshness, source health, journaling, options chain, replay, and stored evidence.
- Full cloud infrastructure is premature before the screening logic is validated.
- Local FastAPI and SQLite are enough for v1 while keeping credentials and trade data private.
- Read-only plus alerts keeps the safety boundary clean.

### 44.2 Score Separation Rule

TrendForge must not show two scores side by side without explaining the stage.

Correct format:

```text
Stage 1 Pre-Market: ELIGIBLE 23/28
Stage 2 Live: CONFIRMED 14/16 -> READY
```

Definitions:

| Stage | Score | Purpose | Runs |
| --- | --- | --- | --- |
| Stage 1 | 28-point causal score | decides whether the stock has a real reason to be watched | evening, morning, pre-open |
| Stage 2 | 16-point execution score | decides whether the live entry is clean enough now | only after intraday trigger starts |

Rules:

- A stock can be Stage 1 ELIGIBLE but still WAIT if the intraday trigger has not fired.
- A stock cannot enter Stage 2 unless it first passes Stage 1 and all hard gates.
- A high Stage 2 score cannot rescue a weak or fake Stage 1 cause.
- The UI must label both scores with plain meaning, not only numbers.

Example:

```text
INFY
Stage 1: ELIGIBLE 23/28
Reason: real IT sector catalyst, sponsor footprint, clean structure, early flow.

Stage 2: CONFIRMED 14/16 -> READY LONG
Reason: 15-minute high break, VWAP hold, RVOL-TOD 3.2x, long OI build-up.
```

### 44.3 Forced Counterparty Definitions

Forced counterparty must be a named flag, not a vague confidence word.

```text
FORCED COUNTERPARTY RISK/FUEL: HIGH
Reason: promoter pledge 68 percent; margin-call zone approaching.
```

Forced-counterparty scenarios:

| Scenario | Signal | Radar Meaning |
| --- | --- | --- |
| OTM options near expiry going to zero | gamma squeeze or pinning near strikes | fast move or violent reversal possible |
| high short interest with stop cluster above resistance | short covering fuel | upside can accelerate after breakout |
| promoter pledge high or rising | margin-call selling risk | downside cascade possible |
| MF/ETF redemption pressure | DII forced selling even in good stocks | avoid fresh longs unless flow stabilizes |
| FII hedge or currency unwind | banking/index false breakout risk near month-end | downgrade banking breakouts |
| index inclusion/exclusion | passive fund forced buying/selling | flow can override normal chart signals |
| F&O ban or margin pressure | position reduction forced by rule | reject or reduce size |

Implementation rule:

- The stock card must show who is forced, what level triggers them, and whether that forced flow helps or hurts the proposed trade.

### 44.4 NO_TRADE As A Primary Daily State

NO_TRADE is not a fallback. It is a first-class daily output.

TrendForge must be willing to say no stock should be traded today.

Daily NO_TRADE triggers:

- India VIX spikes sharply or crosses configured danger threshold.
- Market breadth is worse than 1:3.
- RBI, budget, Fed, election, war, or major policy event is close enough to distort price.
- GIFT Nifty or index futures reverse direction multiple times before open.
- Sector leadership is absent or contradictory.
- Data confidence is RED for critical feeds.
- Expiry mechanics dominate normal price discovery.
- Funnel shows too many/too few candidates due to abnormal regime, but thresholds are not silently changed.

Example:

```text
TODAY: NO_TRADE ENVIRONMENT
Reason: India VIX +18 percent, breadth 1:3 declining, RBI policy in 2 hours,
GIFT Nifty reversed twice, and no reliable regime is established.
Action: no fresh trades. Reassess at 10:30 AM.
```

Rules:

- NO_TRADE can apply to the whole market, one sector, or one stock.
- NO_TRADE must preserve capital and prevent forced action.
- The UI must show the next reassessment time when possible.

### 44.5 Delivery Percent Timing Correction

Delivery percent is T+1 data and must be labeled as previous-session evidence.

Correct display:

```text
Delivery: 48 percent (yesterday, T+1 data)
Live proxy: RVOL-TOD 3.2x + OI change + VWAP behavior
```

Rules:

- Delivery percent can support sponsor context for swing and next-day planning.
- Delivery percent cannot be treated as live institutional confirmation.
- Intraday sponsor proxy must use RVOL-TOD, order-flow proxy, OI change, VWAP hold/reclaim, bid/ask spread, and option premium concentration where available.

### 44.6 Liquidity Time Window Filter

TrendForge must understand NSE intraday liquidity rhythm.

| Time IST | Window | Radar Rule |
| --- | --- | --- |
| 9:15 to 9:30 | opening volatility | observe, build opening range, do not chase |
| 9:30 to 10:00 | first valid execution window | ORB and gap logic can trigger |
| 10:00 to 11:30 | clean momentum window | strongest normal intraday entry window |
| 11:30 to 1:00 | lunch trap | suppress new READY signals unless exceptional activity exists |
| 1:00 to 2:30 | institutional resume window | trend resumption can be valid |
| 2:30 to 3:15 | closing push/squaring | manage exits, special expiry behavior |
| 3:15 to 3:30 | closing mechanics | exit intraday unless swing thesis exists |

Lunch trap rule:

- A new READY signal between 11:30 and 1:00 becomes WAIT_LOW_LIQUIDITY unless RVOL-TOD is above 3.0x or a verified catalyst/expiry mechanism is active.

Example:

```text
WAIT_LOW_LIQUIDITY
Reason: signal fired at 11:45 AM during lunch trap; RVOL-TOD only 1.1x.
Action: wait for 1:00 PM retest or RVOL-TOD > 3.0x.
```

### 44.7 Gap Fade Counter-Setup

Pre-open gap logic must include both continuation and fade outcomes.

Gap fade is a separate setup, not a rejected gap.

```text
GAP FADE WATCH
ADANIENT: +3.1 percent gap, no verified catalyst
Setup: if price fails below pre-open low in first 15 minutes -> SHORT for gap fill
Target: previous day's close
Invalidation: reclaim and hold above opening range high with RVOL-TOD > 2.0x
```

Rules:

- Empty gap means gap without confirmed catalyst, sector support, or sponsor evidence.
- Empty gap up with weak breadth can become a short watch.
- Empty gap down in strong regime can become a long reclaim watch.
- Historical fill probability must be tracked in the journal instead of assumed permanently.
- Gap fade cannot trigger during RED data confidence or abnormal event conditions.

### 44.8 Expiry Mode Rules

Expiry behavior must be driven by the actual NSE contract calendar and contract master, not a hardcoded weekday.

Current planning assumption:

- NIFTY weekly and monthly options use Tuesday expiry according to current NSE contract specifications.
- If NSE changes expiry rules again, TrendForge must update from the contract master and show the active expiry date in the UI.

Expiry-mode lifecycle for current Tuesday expiry:

| Timing | Behavior To Watch | Radar Adjustment |
| --- | --- | --- |
| Friday/Monday before expiry | positioning, weekend risk, max-pain pull can begin | raise options and event weights |
| Tuesday morning | gamma accelerates, false breakouts common | require stronger confirmation |
| Tuesday 2:00 to 3:00 PM | option-seller adjustment, covering, pinning or squeeze | show expiry warning on all index-linked stocks |
| Tuesday last 30 minutes | settlement mechanics | avoid fresh intraday entries unless planned |
| monthly expiry | stronger stock-option and index-option distortion | reduce size and tighten invalidation |

Expiry-mode fields:

- active expiry date
- days to expiry
- max pain
- call/put OI walls
- IV rank
- expected move
- gamma flip
- GEX regime
- premium concentration
- pin risk
- squeeze risk
- IV crush risk after event/expiry

Rules:

- Expiry mode can upgrade FLOW only when CAUSE and SPONSOR are already valid.
- Expiry mode can downgrade or block trades when gamma/pinning makes the setup unreliable.
- Options Greeks and GEX are confirmation/risk tools, not standalone trade signals.

### 44.9 RRG Sector Rotation Logic

Sector heatmap is not enough. TrendForge must show sector rotation status.

Daily sector RRG states:

| State | Meaning | Action |
| --- | --- | --- |
| Leading | strong relative strength and improving momentum | prefer long setups |
| Improving | weak current strength but improving momentum | early accumulation watch |
| Weakening | still strong but momentum declining | reduce long aggression |
| Lagging | weak strength and weakening momentum | avoid longs or consider shorts |

Example:

```text
SECTOR RRG STATUS
IT: Leading -> buy setups allowed
Banking: Improving -> early accumulation watch
Metals: Lagging -> avoid longs/short watch
FMCG: Weakening -> reduce long size
```

Rules:

- Long candidates should prefer Leading or Improving sectors.
- Short candidates should prefer Lagging or Weakening sectors.
- A sector-specific catalyst can override sector state only with strong source evidence.
- RRG state must feed the Stage 1 causal score and Live Radar display.

### 44.10 Portfolio Correlation Block

Position sizing must check portfolio-level risk, not only single-trade risk.

Example:

```text
OPEN POSITION WARNING
INFY Long
HCLTECH Long
TCS Long just triggered

Portfolio correlation: 0.85+
Theme: all IT
Effective risk: 3x single-trade risk
Action: block new TCS or reduce size until total sector risk is within limit.
```

Rules:

- If correlation to open positions is above 0.70, show SAME_BET warning.
- If same sector/theme exposure exceeds limit, block or reduce the new position.
- Small accounts should default to maximum 2 to 3 open positions unless risk settings are changed.
- Effective risk must include correlated positions, not only the new stop-loss amount.

### 44.11 Operator Activity Hard-Block

India-specific operator activity must be a hard-block, not a soft warning.

Operator flags:

| Pattern | Flag | Action |
| --- | --- | --- |
| price up 10 to 15 percent in 3 days, no news, delivery below 15 percent | OPERATOR_WARNING | reject |
| repeated circuits without verified catalyst | CIRCUIT_OPERATOR_RISK | reject |
| penny stock below INR 20 with RVOL spike above 50x | PENNY_PUMP_RISK | reject |
| SME stock suddenly liquid without institutional source | SME_LIQUIDITY_MIRAGE | reject |
| low free float plus sudden breakout and poor delivery | FLOAT_TRAP | reject |
| ASM/GSM or surveillance list | SURVEILLANCE_RISK | reject |

Circular-trading note:

- Public data may not reveal same-counterparty circular trading directly.
- If direct surveillance data is unavailable, TrendForge must use public proxy flags and label confidence honestly.

Rule:

- Operator hard-block cannot be overridden by high technical score, high RVOL, or breakout strength.

### 44.12 Crisis And Scenario Panel

TrendForge needs a visible regime override bar on every screen.

```text
REGIME OVERRIDE: RED
Scenario: policy/war/recession/Fed/RBI shock
Instruction: no fresh trades until volatility and breadth stabilize.
```

Scenario inputs:

- war/geopolitical escalation
- recession shock
- Fed/RBI surprise
- budget day
- election result day
- currency shock
- crude shock
- bank/credit event
- exchange/broker/data outage

Rules:

- Regime override can block all stock-level READY signals.
- The reason must be visible at the top of every screen.
- The system must provide reassessment timing.

### 44.13 Options Deep Dive Screen Requirements

For F&O stocks and index-linked trades, TrendForge must include an Options Deep Dive.

Required fields:

- IV rank
- IV percentile where available
- option chain OI walls
- change in OI by strike
- call/put volume concentration
- PCR
- GEX and gamma flip
- squeeze zone
- pin zone
- expected move
- max pain
- event straddle price
- optimal strike selector by liquidity, spread, delta, and invalidation distance
- Greeks: delta, gamma, theta, vega where available or calculated
- warning when Greeks are estimated instead of broker-provided

Rules:

- Option buying must show theta decay and IV crush risk.
- Option selling must show tail risk, margin risk, and event risk.
- Strike selection must prefer liquid strikes with tight spreads.
- The options screen does not create trades without equity/market context.

### 44.14 Two-Week Event Calendar

The dashboard must show forward event risk, not only today's events.

Required calendar horizon:

```text
Next 14 calendar days
```

Events to show:

- RBI policy/minutes
- Fed decision/minutes
- Union budget or major policy event
- company results
- ex-dividend, split, bonus, rights
- MSCI/FTSE/Nifty rebalance
- F&O expiry
- stock entering/leaving F&O ban
- major economic data
- court/regulatory events where known

Example:

```text
EVENT CALENDAR
RBI policy: in 4 days
TCS results: in 2 days
NIFTY expiry: in 3 days
MSCI rebalance: in 12 days
```

Rules:

- Event proximity can reduce size, block new entries, or move a stock from READY to WAIT.
- Event calendar must feed both Stage 1 and risk sizing.

### 44.15 Cross-Market Driver Row

Every stock card should show its main external driver when relevant.

Example:

```text
TATASTEEL
Driver: LME copper -2 percent, China PMI missed
Impact: driver against stock
Radar: downgrade long setup unless stock-specific sponsor is strong
```

Driver map examples:

- IT: Nasdaq, USD/INR, US tech spending, DXY
- metals: LME metals, China data, dollar
- oil marketing: crude oil, refining margins
- airlines/paints: crude and INR
- banks/NBFCs: RBI rates, bond yields, liquidity, FII index flow
- gold financiers: gold price, rural liquidity
- exporters: USD/INR and global demand

Rule:

- Cross-market driver conflict must be shown as a visible downgrade, not hidden inside score.

### 44.16 Funnel Visualization

The Live Radar must show how many stocks survive each layer.

Example:

```text
FUNNEL
Universe: 1800
Tradable after hard filters: 400
Regime/sector aligned: 120
Causal pass: 18
Live confirmed: 5
READY: 2
WAIT: 3
REJECT: 115
```

Rules:

- If funnel output is zero, show which gate is blocking.
- If funnel output is too large, show which filters are loose.
- Funnel can recommend strict/normal/exploratory profiles.
- Funnel cannot silently relax thresholds in actionable mode.

### 44.17 System Health And Settings

System Health must be visible before the user trusts any signal.

Required health checks:

- NSE feed freshness
- broker/API feed freshness if used
- options chain freshness
- FII/DII data date
- delivery data date
- corporate actions date
- event calendar freshness
- database write status
- last scanner run time
- stale source warnings

Settings screen must allow editing without code changes:

- account capital
- risk per trade
- maximum open positions
- sector exposure cap
- correlation cap
- data source credentials/API keys
- Telegram or alert token
- strict/normal/exploratory threshold profile
- intraday/swing mode defaults
- paper/live-read-only mode

### 44.18 Swing Manager

Swing trades need a separate manager because they last days or weeks.

Required fields:

- original thesis
- current thesis status
- daily rescore
- event risk ahead
- trailing stop evolution
- unrealized R multiple
- sector/RRG state change
- sponsor evidence update
- exit reason if thesis weakens

Rules:

- Swing trade must be rescored daily.
- If thesis is broken, exit or reduce even if stop has not hit.
- Fresh event risk can move a swing position from HOLD to REDUCE.

### 44.19 Journal Accuracy And Equity Curve

Journal must measure whether the system actually improves decisions.

Required analytics:

- equity curve
- daily P&L
- R multiple distribution
- win rate by setup
- expectancy by score bucket
- false READY rate
- WAIT that later became winner
- REJECT that saved loss
- NO_TRADE day outcome
- market-bias accuracy
- sector-call accuracy
- data-confidence impact

Example:

```text
SYSTEM ACCURACY
System said BULLISH: correct 73 percent of last 30 days
System said AVOID: saved loss 81 percent of the time
Score above 20 trades: 64 percent win rate
Score below 15 trades: 28 percent win rate
```

Rules:

- These percentages are examples until enough journal data exists.
- The app must calculate them from recorded decisions, not manual memory.

### 44.20 Small Account Risk Rule

Default account example must match a small account unless the user changes settings.

Example:

```text
Account: INR 1,00,000
Risk: 0.5 percent = INR 500
Entry: INR 445
Stop: INR 432
Risk/share: INR 13
Size: 38 shares
Position value: INR 16,910
Max loss: INR 494
Small-account note: keep maximum 2 to 3 positions open unless risk is deliberately changed.
```

Rules:

- Account size is configurable in Settings.
- Position size must use account risk, not desired profit.
- Correlated positions reduce allowed size.

### 44.21 Final Screen Inventory

The final planned UI includes the original 8 screens plus assessment additions.

| Screen | Name | When |
| --- | --- | --- |
| 0 | System Health + Regime Override Bar | always visible |
| 1 | Evening Prep | 7 PM to 10 PM |
| 2 | Morning Brief | 6 AM to 9 AM |
| 3 | Pre-Open Scanner | 9:00 AM to 9:15 AM |
| 4 | Live Radar + Shortlist | 9:15 AM onward |
| 5 | Stock Deep Dive | anytime |
| 5b | Options Deep Dive | anytime for F&O stocks |
| 6 | Position Sizing | before trade |
| 7 | Trade Monitor Intraday | after entry |
| 7b | Swing Manager | after swing entry |
| 8 | Journal + Learning + Equity Curve | after market |
| 9 | Event Calendar | anytime |
| 10 | Settings | anytime |

Embedded panels:

- Why Rejected tab inside Live Radar
- WAIT Board inside Live Radar
- Funnel View inside Live Radar
- Replay Mode inside Journal
- Data Confidence badge across all screens
- Breadth Danger Alarm across market screens
- Forced Counterparty card inside stock deep dive
- Cross-Market Driver row inside stock cards

### 44.22 Updated Build Order

Build order after this merge:

1. Backend skeleton: FastAPI server, SQLite schema, health endpoint, config model.
2. Data pipelines: NSE data, FII/DII, delivery, bulk/block, corporate actions, events, options chain, sector indices, cross-market drivers.
3. Screening engine: hard filters, 8-layer gates, 28-point causal score, gap scanner, trap detection, operator blocks.
4. Intraday radar engine: Stage 2 execution score, liquidity window filter, gap fade, expiry mode, RVOL-TOD, OI/option confirmation.
5. Frontend: Screen 0 to Screen 10, embedded panels, data confidence badges, NO_TRADE state.
6. Risk engine and journal: position size, correlation risk, small-account limits, equity curve, replay, system accuracy.
7. Testing and validation: stale data, trap hard-blocks, expiry calendar, gap fade, score separation, no silent threshold relaxation.

### 44.23 Output Contract After Assessment Merge

Every stock response must include:

```text
State: READY / WAIT / REJECT / NO_TRADE
Direction: LONG / SHORT / WATCH
Stage 1 Causal Score: x/28 with CAUSE, SPONSOR, STRUCTURE, FLOW
Stage 2 Execution Score: x/16 if live trigger exists
Percentile Rank
Sector RRG State
Market Regime
Liquidity Window State
Expiry Mode State
Forced Counterparty Flag
Cross-Market Driver
Delivery Label: previous-session/T+1
Live Flow Proxy: RVOL-TOD/OI/VWAP/options
Reason
Evidence with source/date
Entry trigger
Stop
Targets
Position size
Portfolio correlation warning
Trap warning
Operator warning
Exit plan
Data confidence
Next reassessment time if WAIT or NO_TRADE
```

Minimum examples:

```text
READY LONG: INFY
Stage 1: ELIGIBLE 23/28
Stage 2: CONFIRMED 14/16
Reason: IT sector Leading, Nasdaq support, clean catalyst, delivery 48 percent yesterday, RVOL-TOD 3.2x, VWAP hold, long OI build-up.
Entry: above 15-minute high
Stop: below VWAP/reclaim failure
Position Size: based on INR 1,00,000 account and 0.5 percent risk
Data Confidence: GREEN
```

```text
WAIT_LOW_LIQUIDITY: RELIANCE
Reason: setup triggered at 11:47 AM during lunch trap and RVOL-TOD is only 1.2x.
Action: wait for 1:00 PM retest or RVOL-TOD > 3.0x.
```

```text
REJECT_OPERATOR_RISK: ABC
Reason: price up 14 percent in 3 days, no verified news, delivery below 15 percent, low free float.
Action: hard block; technical breakout score ignored.
```

```text
NO_TRADE ENVIRONMENT
Reason: VIX spike, poor breadth, major event pending, and conflicting pre-open direction.
Action: no fresh trades; reassess at stated time.
```

## 45. Trader Safety And Emotional Emergency Layer

This layer is mandatory before live use.

TrendForge must protect the trader from emotional damage and capital damage, not only identify opportunities. A screener that finds stocks but allows revenge trading, panic trading, over-sizing, or trading during unsafe mental state is incomplete.

This layer sits above normal scoring.

Priority order:

1. Data/regulatory hard fail.
2. Operator/manipulation hard fail.
3. Account safety hard fail.
4. Trader emotional safety hard fail.
5. Market regime and crisis override.
6. Stock/sector/setup scoring.

If the safety layer blocks trading, no score can override it.

### 45.1 Safety Output States

Additional safety states:

| State | Meaning | User Action |
| --- | --- | --- |
| LOCKED_NO_TRADE | trading is blocked by safety rule | no new trades |
| DAILY_STOP_HIT | daily loss or drawdown limit reached | stop trading for the day |
| COOLDOWN_ACTIVE | user is inside forced pause period | wait until timer ends |
| WAIT_EMOTIONAL_RISK | setup exists but user behavior or checklist indicates emotional risk | do not enter yet |
| WAIT_RECOVERY_REVIEW | user must journal/review before new trade | complete review |
| BROKER_DATA_TRAUMA | broker/feed failure or abnormal execution risk | stop new entries |

Rules:

- READY can be downgraded to WAIT_EMOTIONAL_RISK, COOLDOWN_ACTIVE, DAILY_STOP_HIT, or LOCKED_NO_TRADE.
- Safety states must show reason, timer, and next allowed action.
- Safety blocks must be logged in the journal.

### 45.2 Panic Mode And Manual Lock

TrendForge must include a visible manual panic button.

```text
PANIC MODE: ON
State: LOCKED_NO_TRADE
Reason: user manually activated emergency lock.
Action: no new trades. Existing positions show only risk-reduction actions.
Next step: journal, reassess after cooldown.
```

Rules:

- Panic Mode blocks all new trades immediately.
- Panic Mode does not hide current positions.
- Current positions remain visible with stop, exit, reduce-size, and risk notes.
- User can unlock only after completing the cooldown checklist.
- Unlock action must be journaled with timestamp and reason.

### 45.3 Daily Loss Circuit Breaker

The app must enforce a configurable daily loss stop.

Default planning values:

- hard stop after -1.5R daily realized loss
- hard stop after 2 consecutive full-stop losses
- hard stop after configured percent of account loss, default 1.0 percent
- warning after -1.0R

Example:

```text
DAILY LOSS LIMIT HIT
Loss: -1.5R
State: LOCKED_NO_TRADE
Action: new trades blocked for today.
Reason: protect capital and prevent emotional recovery trading.
```

Rules:

- Daily loss includes realized losses and optionally unrealized open risk.
- The user can configure thresholds in Settings.
- The app must not recommend a trade after DAILY_STOP_HIT.
- The next valid trading session resets the daily counter, but the journal still records the event.

### 45.4 Loss-Streak And Revenge Trading Detector

TrendForge must detect revenge-trading behavior.

Revenge triggers:

- new trade within configured minutes after a loss, default 10 minutes
- increasing size after a losing trade
- switching direction repeatedly in the same stock
- taking a trade during NO_TRADE environment
- entering after missing the original trigger
- taking more than configured trades per day, default 3 to 5
- moving stop wider after entry
- cancelling stop after price moves against position
- entering without position-size confirmation

Example:

```text
WAIT_EMOTIONAL_RISK
Reason: new trade attempted 4 minutes after a full-stop loss and size increased by 2x.
Action: blocked for 20-minute cooldown.
```

Rules:

- Revenge flags do not accuse the user; they protect the account.
- The wording must be factual and calm.
- Repeated revenge flags activate LOCKED_NO_TRADE for the day.

### 45.5 Pre-Trade Emotional Checklist

Before position sizing, the app must ask a short checklist when risk is elevated.

Checklist:

```text
PRE-TRADE SAFETY CHECK
1. Am I chasing after missing the original entry?
2. Am I trying to recover a loss?
3. Am I increasing size because I want to win back money?
4. Is this trade inside today's plan?
5. Did the system mark this stock READY, not WAIT or REJECT?
6. Is my stop already defined and accepted?
7. Can I accept the planned loss without changing the stop?
```

Rules:

- If unsafe answers appear, state becomes WAIT_EMOTIONAL_RISK.
- The checklist must be quick, not a long form.
- The app must not shame the user.
- The app should use direct risk language: "This is not a valid planned trade."

### 45.6 Confidence Versus Evidence Panel

The app must separate user confidence from system evidence.

Example:

```text
CONFIDENCE VS EVIDENCE
User confidence: HIGH
System evidence: LOW
State: WAIT
Reason: emotion is stronger than data. Entry is blocked until evidence improves.
```

Rules:

- User confidence can be captured manually with a simple slider or button.
- High confidence does not increase score.
- Low evidence overrides high confidence.
- This panel should be shown when the user tries to force an entry from WAIT/REJECT.

### 45.7 Market Trauma Modes

TrendForge must recognize abnormal market conditions that can emotionally and technically distort trading.

Trauma modes:

| Mode | Trigger | Action |
| --- | --- | --- |
| FLASH_CRASH_MODE | sudden index fall, spread explosion, liquidity drop | block new entries; manage exits only |
| DATA_OUTAGE_MODE | critical feed stale or inconsistent | block new live decisions |
| BROKER_OUTAGE_MODE | broker/API/order status unreliable | no new trades; show risk-only panel |
| VIX_SHOCK_MODE | India VIX spike beyond threshold | reduce size or NO_TRADE |
| NEWS_PANIC_MODE | unscheduled major news shock | wait for stabilization |
| GAP_TRAP_PANIC_MODE | extreme gap without reliable price discovery | no chase; wait for structure |
| LIMIT_CIRCUIT_MODE | index/stock circuit risk | avoid entries; prioritize exits/risk |

Example:

```text
MARKET TRAUMA MODE: FLASH_CRASH
Reason: index fell 2 percent in 8 minutes, spreads widened, breadth collapsed.
Action: no new entries. Existing trades: reduce risk only.
```

### 45.8 Emergency Support Boundary

TrendForge is not a medical, mental-health, or crisis service.

If the user indicates extreme distress, self-harm thoughts, inability to stop, or unsafe behavior:

- the app must show STOP_TRADING_NOW
- the app must block all new trades
- the app must suggest contacting a trusted person or local emergency support
- the app must not try to provide therapy or crisis counseling

Example:

```text
STOP_TRADING_NOW
Reason: user distress is above trading-safe threshold.
Action: all new trades locked. Step away from the screen and contact trusted support.
```

### 45.9 Safety Journal

Every safety event must be recorded.

Fields:

- timestamp
- safety state
- trigger
- active positions
- realized P&L
- unrealized risk
- trade attempted
- system action
- user override attempt if any
- cooldown duration
- next allowed action

Purpose:

- identify emotional patterns
- improve future rules
- prevent repeat mistakes
- show whether safety rules saved money

### 45.10 Cooldown Rules

Default cooldowns:

| Trigger | Cooldown |
| --- | ---: |
| one full-stop loss | 10 minutes |
| two consecutive losses | rest of session or 60 minutes |
| daily loss warning | 20 minutes and journal required |
| daily loss limit hit | rest of day |
| panic button | user-defined, default 30 minutes |
| data/broker outage | until source health is GREEN |
| revenge flag repeated twice | rest of day |

Rules:

- Cooldown timer must be visible.
- During cooldown, the radar can show analysis but not actionable READY entries.
- After cooldown, the user must complete a short recovery checklist.

### 45.11 Recovery Checklist

Before unlocking after safety block:

```text
RECOVERY CHECKLIST
1. I know the reason trading was locked.
2. I accept today's P&L.
3. I will not increase size to recover loss.
4. I will only take a new trade if TrendForge marks it READY.
5. I accept the next stop-loss before entering.
```

Rules:

- The checklist is a guardrail, not a motivational screen.
- Unlock does not erase the journal record.
- If another safety trigger occurs, lock activates again.

### 45.12 Safety Settings

Settings must include:

- daily max loss in R
- daily max loss as account percent
- max trades per day
- max consecutive losses
- cooldown minutes after loss
- panic-lock duration
- allow/disallow manual override
- small-account strict mode
- emotional checklist always-on toggle
- broker/data outage behavior

Default:

- manual override should be disabled for hard safety locks in v1.

### 45.13 Open-Source Components To Evaluate

These open-source tools can improve TrendForge if licenses, maintenance state, and API stability are verified before implementation.

| Area | Candidate | Use |
| --- | --- | --- |
| Fast backtesting | vectorbt | test many screener rules quickly |
| Event replay/backtesting | Backtrader | candle-by-candle strategy replay |
| Indicators | TA-Lib, ta, pandas-ta-classic | avoid hand-writing common indicators |
| Options Greeks | py_vollib, mibian | IV and Greeks when broker data is missing |
| Portfolio risk | Riskfolio-Lib, skfolio | correlation, risk contribution, portfolio constraints |
| Performance analytics | QuantStats | equity curve, drawdown, returns report |
| Trading calendars | exchange_calendars | exchange session and holiday logic |
| Local analytics | DuckDB | fast local historical scans |
| Fast dataframes | Polars | high-speed data processing |
| Charts | TradingView Lightweight Charts, Apache ECharts, uPlot | candlestick and radar visuals |
| Tables | AG Grid Community | professional scanner grid |
| NSE adapters | nselib, jugaad-data, NseIndiaApi, nsepython | data adapter candidates with fallback wrappers |

Rules:

- Open-source libraries are implementation aids, not business logic replacements.
- Every external data adapter must sit behind TrendForge's own adapter interface.
- Unofficial NSE adapters can break; use health checks, caching, and fallbacks.
- Options Greeks calculated locally must be labeled ESTIMATED.
- Backtest results must be point-in-time and must avoid lookahead bias.

### 45.14 Final Safety Principle

TrendForge's final priority order:

```text
If market evidence is weak, WAIT.
If data is stale, WAIT or REJECT.
If risk is too high, NO_TRADE.
If the user is emotionally unsafe, LOCKED_NO_TRADE.
Capital protection comes before opportunity.
```

## 46. Smart Money, OI, Volume, Basis, And Price-Acceptance Confluence Engine

This section is a mandatory upgrade. It makes TrendForge understand whether a smart-money signal is actually being confirmed by live market behavior.

The final question is not:

```text
Did smart money buy?
```

The final question is:

```text
Did smart money buy, did price accept that level, did volume confirm, did OI confirm, did futures basis confirm, did options IV confirm, and is the user safe to act?
```

No old rule is removed. This section strengthens the existing Smart Money, FLOW, Options, Risk, and Safety layers.

### 46.1 Documents And Future Ownership

This confluence engine must be treated as part of the future build requirements.

Authoritative locations:

- `SCREENER_RULES.md`: business logic and gates.
- `DASHBOARD_EXPERIENCE_PLAN.md`: screen behavior and user output.
- `ASSESSMENT_RADAR_UPGRADE_PLAN.md`: audit/merge record.
- `CONFLUENCE_ENGINE_UPGRADE_PLAN.md`: standalone future reference.

Future agents must not downgrade this to a simple numeric score. The named-state output is required.

### 46.2 Updated 10-Layer Decision Engine

The previous 8-layer pipeline remains valid. Two explicit layers are added:

- Layer 7A: Price Acceptance And Anchor Layer.
- Layer 9: Emotional Safety Gate.

```text
SCREEN 0 COMMAND BAR: always visible
System health, regime, VIX, breadth, expiry mode, liquidity window, trader safety, NO_TRADE override

Layer 0: Global Macro Gate
US/Asia/intermarket, GIFT Nifty, FII/DII, news, currency, commodities

Layer 1: Market Regime Gate
Trend, VIX, breadth, index participant OI, index futures/option context

Layer 2: Sector Gate
Sector heatmap, RRG momentum, sector rotation phase, cross-market drivers

Layer 3: Stock Safety Filter
Liquidity, spread, traded value, MWPL, F&O ban, ASM/GSM, operator flag, surveillance

Layer 4: Smart Money Layer
Graded insider trades, SAST/PIT, bulk/block deals, MF/FPI holdings, pledge, SLB borrow proxy, policy beneficiary, DIPAM

Layer 5: OI + Volume + Basis Layer
OI quadrant, MWPL-safe check, futures basis/cost of carry, rollover, IV confluence, RVOL-TOD, trade count, average trade size, volume location

Layer 6: Setup Identification
Gap&Go, ORB, VCP, PEAD, pullback, 21 EMA, relative strength

Layer 7A: Price Acceptance And Anchor Layer
Deal price anchor, event AVWAP, FOMO distance, supply overhang, absorption/rejection

Layer 8: Risk Engine
Stop, target, R:R, position size, slippage, margin, portfolio correlation, sector exposure

Layer 9: Emotional Safety Gate
Recent loss, daily loss, FOMO, revenge behavior, cooldown, lock states

Layer 10: Execution And Post-Entry
Order type, timing window, live monitor, trailing stop, add/exit rules, journal
```

### 46.3 Screen 0 Command Bar Requirement

Screen 0 must be persistent across all pages.

Example:

```text
COMMAND BAR
System: GREEN | Regime: TRADEABLE BULLISH | India VIX: Normal
Breadth: 1.8:1 Positive | Expiry Mode: OFF | MWPL Watch: 2 stocks
Liquidity Window: ACTIVE | Trader Safety: GREEN | NO_TRADE Override: OFF
```

If hostile:

```text
COMMAND BAR
System: AMBER | Regime: CHOPPY | India VIX: Elevated
Breadth: Weak | Expiry Mode: ON | Liquidity Window: LUNCH TRAP
Trader Safety: COOLDOWN_ACTIVE | NO_TRADE Override: PARTIAL
```

Rules:

- Every stock card must inherit warnings from the command bar.
- READY cannot be shown without visible context from command bar.
- Expiry Mode, MWPL Watch, Liquidity Window, and Trader Safety can downgrade stock-level output.

### 46.4 OI Quadrant Logic

OI must be interpreted as a named state, not just "bullish" or "bearish".

| Price | OI | Named State | Meaning | Sustainability |
| --- | --- | --- | --- | --- |
| up | up | LONG_BUILD_UP | fresh longs entering | stronger if volume and basis confirm |
| up | down | SHORT_COVERING | shorts exiting | can be sharp but may be temporary |
| down | up | SHORT_BUILD_UP | fresh shorts entering | bearish if volume confirms |
| down | down | LONG_UNWINDING | longs exiting | bearish/weak, often exhaustion |

Rules:

- LONG_BUILD_UP and SHORT_COVERING both move price up, but they are not equal.
- LONG_BUILD_UP is more sustainable than pure SHORT_COVERING.
- Expiry week and MWPL state must be checked before trusting the quadrant.
- The named OI state must appear on every F&O stock card.

Example:

```text
OI Quadrant: LONG_BUILD_UP
Reason: price +2.1 percent, futures OI +9.4 percent.
Interpretation: fresh positions are being built, not only shorts exiting.
```

### 46.5 MWPL And F&O Ban Reliability Gate

MWPL must be checked before OI interpretation.

| MWPL Usage | State | OI Reliability | Action |
| ---: | --- | --- | --- |
| below 80 percent | SAFE | normal | OI can be interpreted normally |
| 80 to 90 percent | MWPL_YELLOW | caution | show warning |
| 90 to 95 percent | MWPL_ORANGE | unreliable/distorted | downgrade OI confirmation |
| above 95 percent or ban list | MWPL_RED / FNO_BAN | OI signal invalid for fresh positioning | hard block fresh derivative trades |

Rules:

- If MWPL is above 90 percent, OI build-up may be forced closing or ban-driven distortion.
- If a stock is in F&O ban, do not treat OI movement as clean conviction.
- MWPL must be shown before futures/options OI conclusions.

Example:

```text
MWPL: 92 percent ORANGE
OI signal: unreliable
Action: WAIT, do not trust long-build-up classification.
```

### 46.6 Futures Basis And Cost Of Carry

Futures basis:

```text
basis = futures_price - spot_price
basis_percent = basis / spot_price
```

Interpretation:

| Price | OI | Basis | Meaning |
| --- | --- | --- | --- |
| up | up | premium rising | strongest long build-up |
| up | up | premium falling | caution, commitment weakening |
| up | up | discount/negative | conflict, possible hedge or expiry distortion |
| down | up | discount widening | stronger bearish pressure |
| flat | up | basis rising | positioning before price move, watch |

Rules:

- Rising basis plus rising price plus rising OI is high-quality futures confirmation.
- Falling basis while price rises is a warning.
- Negative basis with smart-money buying requires caution, not automatic READY.
- Basis interpretation must account for expiry, dividend/corporate action, and liquidity.

### 46.7 Rollover Data Near Expiry

Near expiry, OI falling may simply be expiry settlement. It must not be misread as long unwinding or short covering without rollover context.

Required rollover checks:

- current-expiry OI change
- next-expiry OI change
- rollover percentage
- rollover cost
- price relative to current and next futures
- max pain and OI walls

Interpretation:

| Current Expiry OI | Next Expiry OI | Meaning |
| --- | --- | --- |
| falling | rising | position carried forward |
| falling | flat/down | position closing |
| rising near expiry | rising | aggressive late build-up |
| falling fast with price stable | expiry unwind/noise, wait for next series |

Rules:

- Expiry Mode must modify OI interpretation.
- Rollover carried forward in same direction strengthens the thesis.
- No next-expiry build means the move may be ending.

### 46.8 Options IV And OI Confluence

IV rank alone is not enough. Direction of IV and interaction with OI are required.

| Options Behavior | Meaning | Action |
| --- | --- | --- |
| call buying + IV rising + call OI rising | aggressive bullish demand | confirm if price/volume align |
| put buying + IV rising + put OI rising | aggressive bearish demand | bearish confirmation |
| OI rising + IV falling | writing/pinning, not directional demand | do not treat as breakout fuel |
| IV spike both calls and puts | event fear/straddle buying | warn about volatility and IV crush |
| high IV rank before event | option buying dangerous | warn or block option-buying setup |
| IV crush after result/event | premium decay risk | avoid stale option entries |

Rules:

- Label whether options flow is directional buying, writing/pinning, event fear, or post-event crush.
- For option buys, the card must show theta and IV crush risk.
- Estimated Greeks must be labeled ESTIMATED.

### 46.9 Deal Price Anchor

Every meaningful smart-money transaction creates an anchor price.

Anchor sources:

- bulk deal price
- block deal price
- insider open-market buy price
- promoter sale price
- PE/co-founder sale price
- result-day opening/close range
- breakout trigger price

Interpretation:

| Price Relative To Anchor | Meaning |
| --- | --- |
| above anchor and holding | smart-money price accepted |
| at anchor with volume absorption | important defense/test |
| below anchor with rising sell volume | smart-money signal failed or supply pressure active |
| far above anchor | valid only if not overextended by ATR/FOMO rules |

Example:

```text
Deal Anchor: FII bulk deal at INR 7,840
Current: INR 7,862
State: ACCEPTED
Reason: price is above FII cost and holding above anchor.
```

Rules:

- A bullish smart-money signal is not active forever.
- If price breaks below the anchor, downgrade to WAIT or REJECT depending on volume and seller type.
- Deal anchor must be monitored live after the event.

### 46.10 Anchored VWAP From Key Events

AVWAP must be tracked from important dates because daily VWAP resets and misses institutional cost basis over time.

Required AVWAP anchors:

- insider open-market buy date
- bulk/block deal date
- result day
- breakout day
- major policy/order announcement day
- large promoter/PE sale day

Interpretation:

| Price Relative To AVWAP | Meaning |
| --- | --- |
| above event AVWAP | market accepting event price |
| reclaiming AVWAP | potential renewed strength |
| rejecting from AVWAP | supply/resistance |
| below result-day AVWAP | PEAD failure risk |

Rules:

- Price above deal anchor but below event AVWAP is a mixed signal.
- Price above multiple event AVWAPs improves conviction.
- AVWAP breaks must feed trap detection and WAIT/REJECT logic.

### 46.11 Smart Money Quality Grading

Every insider/sponsor signal must be classified before scoring.

| Signal Type | Grade | Score Impact |
| --- | --- | --- |
| CEO/promoter open-market buy with own money | very strong | maximum sponsor upgrade |
| repeated promoter buys over multiple days | very strong | high conviction |
| named FII/MF bulk deal at premium | very strong | high sponsor upgrade |
| block deal by high-quality institution at market | medium/strong | moderate sponsor upgrade |
| token director buy below meaningful value | low | small or no upgrade |
| ESOP exercise/allotment | weak/neutral | no conviction upgrade |
| inter-se promoter transfer | neutral | no directional upgrade |
| pledge release | positive | risk reduction |
| pledge addition | danger | downgrade |
| promoter/PE/co-founder sale at discount | hard caution | reject or supply-overhang watch |

Rules:

- ESOP exercise must not be scored as open-market conviction.
- Inter-se transfers must not be scored as new buying.
- Token buys must be scaled by market cap, salary/role, and normal transaction size.
- Seller quality and remaining holding must feed supply overhang.

### 46.12 Volume Quality Metrics

Volume confirmation must go beyond RVOL.

Required fields:

- RVOL-TOD
- traded value
- delivery percent with T+1 label
- bid-ask spread
- number of trades
- average trade size
- average trade size change versus baseline
- volume location: above VWAP, below VWAP, near high, near low
- candle close location: upper/middle/lower range
- spread-adjusted volume

Interpretation:

| Volume Feature | Institutional Read |
| --- | --- |
| high volume + few large trades | institutional footprint possible |
| high volume + many tiny trades | retail churn possible |
| volume above VWAP | stronger acceptance |
| volume near high with weak close | distribution risk |
| volume near low with strong reclaim | absorption risk/accumulation |
| average trade size rising | bigger participants entering |

Rules:

- Same volume can mean different things depending on trade count and location.
- Volume quality must be displayed separately from raw volume.
- Volume spike without price acceptance is not confirmation.

### 46.13 SLB Borrow Data Proxy

India does not publish a clean US-style stock-wise short-interest report, but NSE SLB data can be used as a short-pressure proxy where available.

Required SLB fields when available:

- borrow quantity
- lend quantity
- borrow rate/fee
- quantity on loan
- utilization proxy if derivable
- rate change versus recent baseline

Interpretation:

| SLB Behavior | Meaning |
| --- | --- |
| borrow rate rising sharply | short demand increasing |
| high borrow rate + price breakout | squeeze candidate |
| high borrow rate + weak price | shorts in control |
| borrow demand falling after breakout | short covering may be ending |

Rules:

- SLB is a proxy, not a perfect short-interest number.
- Show confidence level and data freshness.
- If SLB unavailable, say unavailable; do not invent short interest.

### 46.14 Participant-Wise OI Scope Clarification

Participant-wise OI is market/regime context, not stock-level FII proof.

Correct labels:

```text
Participant OI: index/regime signal
Stock-level FII evidence: bulk deal, FPI holding change, delivery/RVOL proxy, filings
```

Rules:

- Do not claim participant-wise OI proves FII buying in a specific stock.
- Use participant OI for Nifty/BankNifty regime, hedge pressure, and broad risk appetite.
- Stock-level institutional evidence must come from stock-specific filings, deals, holdings, delivery, and price/volume behavior.

### 46.15 Supply Overhang Tracking

Large selling creates future supply risk.

Track:

- seller identity
- seller type: promoter, PE, co-founder, strategic investor, MF, FII
- sold quantity/value
- sale price relative to market
- remaining holding
- likely lock-up or future sale schedule if public
- time since sale
- price absorption after sale
- volume at sale level

Supply states:

| State | Meaning | Action |
| --- | --- | --- |
| SUPPLY_OVERHANG_HIGH | motivated seller still owns large remaining stake | avoid or reduce size |
| SUPPLY_ABSORBED | price held/recovered after large sale with strong volume | supply risk reduced |
| SUPPLY_REJECTION | price failed below sale anchor | reject/short watch |

Rule:

- If a motivated seller still holds more than 10 percent and recently sold, show SUPPLY_OVERHANG unless price has clearly absorbed the sale over time.

### 46.16 FOMO Price Check

A good stock can become a bad trade if the user is late.

FOMO rule:

```text
if current_price > ideal_entry + 1x ATR:
    downgrade READY to WAIT_FOMO
```

Additional checks:

- distance from VWAP
- distance from opening range breakout level
- distance from deal anchor and AVWAP
- candle extension and wick size
- volume still expanding or fading
- supply wall above

Example:

```text
WAIT_FOMO
Reason: current price is 1.4 ATR above ideal entry. You missed the clean entry window.
Action: wait for pullback, VWAP retest, or next valid setup.
```

Exception:

- If volume is still expanding, basis is rising, OI is LONG_BUILD_UP, no supply wall exists, and risk can still be defined, the stock can remain PRIORITY_RADAR but must not be chased blindly.

### 46.17 Final Named Output State Machine

Final output must be a named state, not only a score.

| State | Meaning | Output |
| --- | --- | --- |
| PRIORITY_RADAR | high-quality stock, all major confluence layers align | show full card, wait/entry trigger |
| READY | all gates pass and entry trigger is active | show executable plan |
| WAIT | good candidate missing one required confirmation | show missing condition and recheck time |
| WAIT_FOMO | setup is valid but price is too extended from ideal entry | block chase; wait for pullback |
| WAIT_EMOTIONAL | user behavior/risk state unsafe | cooldown or checklist |
| WAIT_OI_UNRELIABLE | MWPL/expiry/rollover distorts OI | do not trust derivative confirmation |
| WAIT_BASIS_CONFLICT | futures basis conflicts with price/OI | wait for basis confirmation |
| WAIT_SUPPLY_OVERHANG | seller supply can cap rally | wait for absorption |
| REJECT | hard fail or broken thesis | show exact failed gate |
| SHORT_WATCH | bearish confluence but short trade needs trigger/risk validation | show short setup conditions |
| NO_TRADE | market/day unsafe | preserve capital |
| LOCKED_NO_TRADE | account or emotional safety lock | hide new picks |
| STOP_TRADING_NOW | distress/panic boundary | stop trading activity |

### 46.18 Final Confluence Decision Matrix

| Smart Money | OI Quadrant | Volume Quality | Futures Basis | Price Acceptance | Final State |
| --- | --- | --- | --- | --- | --- |
| strong open-market/institutional buy | LONG_BUILD_UP | RVOL > 2, large avg trade | premium rising | above deal anchor and AVWAP | PRIORITY_RADAR |
| strong | SHORT_COVERING | RVOL > 2 | flat | above AVWAP | READY, but sustainability warning |
| medium | LONG_BUILD_UP | RVOL > 1.5 | flat | above deal anchor | READY or WAIT depending setup |
| strong | LONG_BUILD_UP | RVOL < 1.5 | premium rising | price 2x ATR past entry | WAIT_FOMO |
| strong | LONG_BUILD_UP | RVOL > 2 | discount/negative | below AVWAP | WAIT_BASIS_CONFLICT |
| weak ESOP/token only | LONG_BUILD_UP | high raw volume | premium | above anchor | WAIT, smart money weak |
| strong | any | any | any | MWPL > 90 percent | WAIT_OI_UNRELIABLE |
| bearish promoter/PE sale at discount | SHORT_BUILD_UP | high volume | discount | below deal anchor | REJECT or SHORT_WATCH |
| any | any | any | any | daily loss/safety lock | LOCKED_NO_TRADE |

Rules:

- The matrix overrides a flat numeric score.
- Hard gates still override the matrix.
- If rows conflict, choose the safer state and show the conflict.

### 46.19 Upgraded Stock Intelligence Card Contract

Every deep-dive card for F&O stocks must include:

```text
STOCK INTELLIGENCE
Status: PRIORITY_RADAR / READY / WAIT / WAIT_FOMO / REJECT / NO_TRADE

Command Bar Context:
System, regime, VIX, breadth, expiry mode, liquidity window, trader safety

Layer 3 Safety:
F&O stock, F&O ban, MWPL percent, ASM/GSM, operator flag, free float, spread

Layer 4 Smart Money:
graded insider trades, bulk/block, MF/FPI, pledge, policy, DIPAM, supply overhang

Layer 5A OI Quadrant:
price change, OI change, named OI state, MWPL reliability

Layer 5B Futures Basis:
spot, futures, basis, basis trend, cost-of-carry interpretation

Layer 5C Volume Quality:
RVOL-TOD, trade count, average trade size, volume location, delivery T+1

Layer 5D IV Confluence:
IV rank, IV direction, options OI, type of options flow, IV crush risk

Expiry/Rollover:
days to expiry, rollover status, next-series OI, max pain, OI walls

Layer 7A Price Acceptance:
deal anchors, event AVWAPs, FOMO distance, supply overhang, absorption/rejection

Layer 8 Risk:
entry, stop, targets, R:R, size, correlation, slippage, margin

Layer 9 Emotional Safety:
recent loss, daily P&L, daily limit usage, FOMO, cooldown, lock state

Confluence Result:
which signals align, which conflict, final named state, next action
```

For non-F&O stocks:

- OI, futures basis, options IV, and MWPL sections must show `NOT APPLICABLE`.
- The card uses smart money, cash volume, delivery, price acceptance, AVWAP, supply, and risk.
- It must never fake OI.

### 46.20 Data Tables Required

Add or extend data storage for:

| Table | Purpose |
| --- | --- |
| derivatives_oi_snapshots | futures/options OI by symbol, expiry, strike, timestamp |
| futures_basis_snapshots | spot, futures, basis, basis percent, carry trend |
| mwpl_snapshots | MWPL usage percent and ban proximity |
| rollover_snapshots | current/next expiry OI and rollover metrics |
| iv_snapshots | IV rank, IV direction, IV by strike/expiry |
| deal_anchors | bulk/block/insider/promoter sale anchors |
| avwap_anchors | event-date AVWAP definitions and current values |
| volume_quality_snapshots | trade count, average trade size, volume location |
| slb_snapshots | borrow quantity, lend quantity, rate, freshness |
| supply_overhang_events | seller, sale size, remaining holding, absorption state |
| confluence_states | final state and reasons for each scan |

### 46.21 Testing Requirements

Minimum tests:

- OI quadrant classification.
- MWPL above 90 percent downgrades OI reliability.
- F&O ban blocks fresh derivative interpretation.
- Basis conflict downgrades READY.
- Rollover prevents expiry-week OI misread.
- IV + OI distinguishes buying from writing/pinning.
- Deal anchor accepted/broken state updates.
- AVWAP reclaim/rejection updates state.
- ESOP exercise scores differently from open-market buy.
- Trade count and average trade size change volume-quality state.
- SLB unavailable does not invent short interest.
- Participant-wise OI is not used as stock-level FII proof.
- WAIT_FOMO triggers when price exceeds ideal entry by more than 1x ATR.
- Supply overhang remains active until absorption evidence clears it.
- LOCKED_NO_TRADE overrides otherwise valid PRIORITY_RADAR.

### 46.22 Open-Source Tools To Evaluate For This Layer

Potential helpers:

| Need | Tool |
| --- | --- |
| vectorized rule backtests | vectorbt |
| event replay | Backtrader |
| fast local analytics | DuckDB |
| fast transforms | Polars |
| indicators and ATR/AVWAP helpers | TA-Lib, ta, pandas-ta-classic |
| options Greeks and IV | py_vollib, mibian |
| entity/name matching | RapidFuzz |
| filing extraction | BeautifulSoup, Playwright, pdfplumber |
| relationship graph | networkx |
| scanner table | AG Grid Community |
| charts/AVWAP anchors | TradingView Lightweight Charts, Apache ECharts |

Rules:

- Use official data where available.
- Keep unofficial adapters behind interfaces and health checks.
- Label estimated calculations clearly.
- Do not allow open-source libraries to silently define business rules.
<!-- HISTORICAL_SOURCE_END path=backup_reference_20260705_162956/backup_screener_rules.md sha256=ee35a478d9358193e74ca56c271c42cdb4a68fcf73ffa004d56ac5d1b70a8bcb -->

<!-- HISTORICAL_SOURCE_BEGIN path=backup_reference_20260705_162956/backup_assessment_radar_upgrade_plan.md sha256=3cabd769625986982bcb577b32d0cf09a20418c41dc89ec5b4408e355a6d9eb5 lines=742 -->
# TrendForge Assessment Radar Upgrade Plan

This file preserves the latest assessment as a standalone merge record.

It does not replace `SCREENER_RULES.md` or `DASHBOARD_EXPERIENCE_PLAN.md`. It records the new radar, screen, and risk requirements that were merged into those files.

## 1. Merge Rule

Nothing from the older plan is deleted.

The following remain active:

- local web dashboard
- FastAPI backend
- SQLite database
- 8-screen daily workflow
- Layer 0 to Layer 8 screening pipeline
- 28-point CAUSE/SPONSOR/STRUCTURE/FLOW causal score
- 16-point live execution score
- options/GEX logic
- trap hard-gates
- data confidence rules
- risk engine
- journal and replay
- no automatic order placement in v1

## 2. Architecture Decision

The v1 build remains:

```text
Local browser dashboard + FastAPI backend + SQLite database
```

Reason:

- Better than single HTML because TrendForge needs live data, source health, alerts, history, options, and journaling.
- Better than full cloud for v1 because cloud adds security, deployment, and credential complexity before logic is validated.
- Local read-only app is safer for the first build.

## 3. Score Clarification

The radar must not show two unexplained scores like:

```text
INFY 23/28 + 14/16
```

Correct display:

```text
Stage 1 Pre-Market: ELIGIBLE 23/28
Stage 2 Live: CONFIRMED 14/16 -> READY
```

Stage 1 decides whether the stock deserves attention. Stage 2 decides whether the live entry is valid now.

## 4. Forced Counterparty Definitions

Forced counterparty must be shown as a named flag.

Examples:

- OTM options near expiry going to zero: gamma squeeze or pinning possible.
- High short interest plus stop cluster above resistance: forced short covering.
- Promoter pledge near danger zone: forced margin-call selling.
- MF/ETF redemption pressure: DII selling even in fundamentally good stocks.
- FII hedge/currency unwind: false banking or index breakout risk.
- Index inclusion/exclusion: passive forced buying or selling.

Output example:

```text
FORCED COUNTERPARTY: HIGH
Reason: promoter pledge 68 percent; margin-call selling zone approaching.
Impact: downgrade long setup or reject if price starts cascading.
```

## 5. NO_TRADE Environment

NO_TRADE is a primary output, not a fallback.

The system must be able to say:

```text
TODAY: NO_TRADE ENVIRONMENT
Reason: VIX spike, weak breadth, major event nearby, and unstable pre-open direction.
Action: no fresh trades. Reassess at 10:30 AM.
```

Triggers:

- India VIX spike
- breadth worse than 1:3
- RBI/Fed/budget/election/war shock
- GIFT Nifty or index futures reversing repeatedly
- no sector leadership
- RED data confidence
- expiry mechanics overpowering normal trend

## 6. Delivery Percent Timing

Delivery percent is T+1 data.

Correct display:

```text
Delivery: 48 percent (yesterday, T+1 data)
Live proxy: RVOL-TOD 3.2x + OI change + VWAP behavior
```

Delivery can support sponsor context. It cannot be treated as live institutional confirmation.

## 7. Liquidity Time Window Filter

TrendForge must understand NSE intraday liquidity.

| Time IST | State | Rule |
| --- | --- | --- |
| 9:15 to 9:30 | opening volatility | observe and build ORB |
| 9:30 to 10:00 | first valid window | ORB/gap triggers allowed |
| 10:00 to 11:30 | clean momentum | best normal entry window |
| 11:30 to 1:00 | lunch trap | suppress new entries unless RVOL-TOD > 3.0x |
| 1:00 to 2:30 | resume window | trend resumption allowed |
| 2:30 to 3:15 | closing push | manage exits and expiry effects |
| 3:15 to 3:30 | closing mechanics | avoid fresh intraday entries |

Output example:

```text
WAIT_LOW_LIQUIDITY
Reason: signal fired at 11:45 AM during lunch trap; RVOL-TOD only 1.1x.
Action: wait for 1 PM retest or RVOL-TOD > 3.0x.
```

## 8. Gap Fade Counter-Setup

Gap scanner must detect both continuation and fade.

```text
GAP FADE WATCH
ADANIENT: +3.1 percent gap, no verified catalyst
Setup: if price fails below pre-open low in first 15 minutes -> SHORT for gap fill
Target: previous close
Invalidation: reclaim opening range high with RVOL-TOD > 2.0x
```

The app must journal actual gap-fill performance instead of trusting a fixed probability forever.

## 9. Expiry Mode

Expiry logic must be based on the actual NSE contract calendar and contract master.

Current planning assumption:

- NIFTY weekly/monthly option expiry is Tuesday under current NSE specifications.
- Do not hardcode old Thursday assumptions.
- If NSE changes expiry rules later, the contract data must drive the UI.

Expiry Mode must show:

- active expiry date
- days to expiry
- max pain
- OI walls
- IV rank
- expected move
- gamma flip
- GEX regime
- pin risk
- squeeze risk
- IV crush risk

## 10. RRG Sector Rotation

Sector heatmap is not enough. Add rotation state.

```text
SECTOR RRG STATUS
IT: Leading -> buy setups allowed
Banking: Improving -> early accumulation watch
Metals: Lagging -> avoid longs or short watch
FMCG: Weakening -> reduce long aggression
```

States:

- Leading
- Improving
- Weakening
- Lagging

## 11. Portfolio Correlation Risk

The risk engine must detect same-bet exposure.

```text
CORRELATION WARNING
Open positions: INFY Long, HCLTECH Long, TCS candidate
Theme: all IT
Portfolio correlation: 0.85+
Effective risk: 3x single-trade risk
Action: block new TCS or reduce size.
```

Small-account default:

```text
Account: INR 1,00,000
Risk: 0.5 percent = INR 500
Max positions: 2 to 3 unless settings are changed
```

## 12. Operator Activity Hard-Block

India-specific operator activity must block trades.

Hard-block patterns:

- price up 10 to 15 percent in 3 days, no verified news, delivery below 15 percent
- repeated circuits without catalyst
- penny stock below INR 20 with 50x to 100x RVOL
- SME stock suddenly liquid without institutional evidence
- low float plus sudden breakout and poor delivery
- ASM/GSM or surveillance list

Operator block overrides all technical scores.

## 13. Crisis And Scenario Panel

The top bar must show crisis/regime override.

```text
REGIME OVERRIDE: RED
Scenario: RBI shock / Fed shock / war / recession / election / budget
Instruction: no fresh trades until volatility and breadth stabilize.
```

## 14. Options Deep Dive

Add a dedicated options screen for F&O stocks.

Required:

- IV rank
- IV percentile where available
- OI walls
- change in OI
- volume concentration
- expected move
- max pain
- GEX and gamma flip
- delta, gamma, theta, vega
- estimated-versus-source Greek badge
- optimal strike selector
- event straddle pricing
- pin/squeeze warning
- IV crush warning

## 15. Two-Week Event Calendar

Show forward risk:

```text
RBI policy: in 4 days
TCS result: in 2 days
NIFTY expiry: in 3 days
MSCI rebalance: in 12 days
```

Events must affect readiness state, size, option IV risk, swing decisions, and NO_TRADE.

## 16. Cross-Market Driver Row

Stock cards must show driver alignment.

```text
TATASTEEL
Driver: LME copper -2 percent, China PMI missed
Impact: driver against long setup
Action: downgrade to WAIT unless stock-specific sponsor is strong.
```

## 17. Funnel View

Live Radar must show survival by layer.

```text
Universe: 1800
Tradable after hard filters: 400
Regime/sector aligned: 120
Causal pass: 18
Live confirmed: 5
READY: 2
WAIT: 3
REJECT: 115
```

The funnel may recommend strict/normal/exploratory profiles, but it must not silently loosen thresholds.

## 18. System Health

System Health must show:

- NSE feed freshness
- options chain freshness
- delivery data date
- FII/DII data date
- event calendar freshness
- database status
- last scanner run
- stale source warnings

## 19. Settings

Settings must let the user change:

- account capital
- risk percent
- maximum open positions
- sector cap
- correlation cap
- data credentials/API keys
- Telegram token
- refresh interval
- strict/normal/exploratory profile
- intraday/swing defaults

## 20. Swing Manager

Swing Manager must show:

- original thesis
- daily rescore
- thesis intact/broken
- event risk
- sector/RRG change
- trailing stop path
- P&L in R
- exit reason

## 21. Journal Accuracy And Equity Curve

Journal must calculate:

- equity curve
- daily P&L
- win rate by setup
- expectancy by score bucket
- market-bias accuracy
- sector-call accuracy
- score above 20 win rate
- score below 15 win rate
- REJECT saved-loss rate
- NO_TRADE day result
- replay mode result

Example percentages in the plan are placeholders until real journal data exists.

## 22. Final Screen List

```text
0   System Health + Regime Override Bar
1   Evening Prep
2   Morning Brief
3   Pre-Open Scanner
4   Live Radar + Shortlist
5   Stock Deep Dive
5b  Options Deep Dive
6   Position Sizing
7   Trade Monitor
7b  Swing Manager
8   Journal + Learning + Equity Curve
9   Event Calendar
10  Settings
```

Embedded:

- Why Rejected tab
- WAIT Board
- Funnel View
- Replay Mode
- Data Confidence badge
- Breadth Danger Alarm
- Forced Counterparty card
- Cross-Market Driver row

## 23. Build Order After This Assessment

1. Backend skeleton: FastAPI, SQLite, settings, health endpoint.
2. Data pipelines: NSE, FII/DII, delivery, bulk/block, corporate actions, options chain, event calendar, sector indices, cross-market drivers.
3. Screening engine: hard filters, 8 layers, causal score, operator blocks, gap scanner, trap detection.
4. Intraday radar: execution score, RVOL-TOD, liquidity window, gap fade, expiry mode, OI/options confirmation.
5. Frontend: Screen 0 to Screen 10, embedded radar panels, NO_TRADE display.
6. Risk and journal: sizing, correlation, small-account rules, equity curve, replay, system accuracy.
7. Validation: stale data, no silent threshold relaxation, expiry calendar, operator hard-blocks, score separation.

## 24. Trader Safety And Emotional Emergency Layer

This is a mandatory upgrade after the emergency-support review.

TrendForge must protect the user from emotional trading, revenge trading, panic trading, and account damage. This layer sits above normal scoring.

Final safety principle:

```text
If market evidence is weak, WAIT.
If data is stale, WAIT or REJECT.
If risk is too high, NO_TRADE.
If the user is emotionally unsafe, LOCKED_NO_TRADE.
Capital protection comes before opportunity.
```

## 25. Safety States

Required states:

- LOCKED_NO_TRADE
- DAILY_STOP_HIT
- COOLDOWN_ACTIVE
- WAIT_EMOTIONAL_RISK
- WAIT_RECOVERY_REVIEW
- BROKER_DATA_TRAUMA
- STOP_TRADING_NOW

These states can override READY.

## 26. Panic Mode

Add a visible panic button.

```text
PANIC MODE ACTIVE
New trades: LOCKED
Existing positions: risk management only
Cooldown: 30 minutes
Required before unlock: recovery checklist
```

Rules:

- block all new trades
- keep open positions visible
- allow only risk reduction
- journal the event
- require cooldown before unlock

## 27. Daily Loss Circuit Breaker

Default planning values:

- warning at -1.0R
- lock at -1.5R
- lock after 2 consecutive full-stop losses
- lock after configured account percent loss

Example:

```text
DAILY LOSS LIMIT HIT
Loss: -1.5R
State: LOCKED_NO_TRADE
Action: no new trades for today
```

## 28. Revenge Trading Detector

Detect:

- trade attempted quickly after loss
- size increased after loss
- repeated direction switching
- trading during NO_TRADE
- chasing after missed trigger
- stop widened or cancelled
- too many trades in one day

Output:

```text
WAIT_EMOTIONAL_RISK
Reason: new trade attempted 4 minutes after a full-stop loss and size increased by 2x.
Action: blocked for cooldown.
```

## 29. Pre-Trade Emotional Checklist

Before sizing, ask:

```text
Am I chasing?
Am I trying to recover a loss?
Did I miss the original entry?
Is this trade inside today's plan?
Is the stock READY, not WAIT or REJECT?
Can I accept the stop-loss without changing it?
```

Unsafe answers change the state to WAIT_EMOTIONAL_RISK.

## 30. Confidence Versus Evidence

Panel:

```text
CONFIDENCE VS EVIDENCE
User confidence: HIGH
System evidence: LOW
State: WAIT
Reason: emotion is stronger than data.
```

User confidence never increases score.

## 31. Market Trauma Modes

Required modes:

- FLASH_CRASH_MODE
- DATA_OUTAGE_MODE
- BROKER_OUTAGE_MODE
- VIX_SHOCK_MODE
- NEWS_PANIC_MODE
- GAP_TRAP_PANIC_MODE
- LIMIT_CIRCUIT_MODE

These modes can block new trades and show risk-only handling for existing positions.

## 32. Emergency Support Boundary

TrendForge is not a medical or crisis-support service.

If the user indicates extreme distress, inability to stop, self-harm thoughts, or unsafe behavior:

```text
STOP_TRADING_NOW
State: LOCKED_NO_TRADE
Action: step away from the screen and contact trusted support or local emergency help.
```

The app must not provide therapy. It must stop trading activity.

## 33. Safety Journal

Every safety event must store:

- timestamp
- safety state
- trigger
- realized P&L
- unrealized risk
- attempted trade
- open positions
- cooldown duration
- override attempt
- next allowed action

## 34. Safety Settings

Settings must include:

- daily max loss in R
- daily max loss as account percent
- max trades per day
- max consecutive losses
- cooldown after loss
- panic-lock duration
- manual override allowed/disallowed
- small-account strict mode
- emotional checklist always-on
- broker/data outage behavior

Default v1 rule:

- no manual override for hard safety locks.

## 35. Open-Source Tools To Evaluate

Useful open-source candidates:

| Area | Candidate | Use |
| --- | --- | --- |
| Fast backtesting | vectorbt | many-rule backtests |
| Event replay | Backtrader | candle-by-candle replay |
| Indicators | TA-Lib, ta, pandas-ta-classic | common indicators |
| Options Greeks | py_vollib, mibian | IV and Greeks |
| Portfolio risk | Riskfolio-Lib, skfolio | risk contribution and correlation |
| Analytics | QuantStats | equity curve and drawdowns |
| Calendars | exchange_calendars | sessions and holidays |
| Local analytics | DuckDB | fast scans |
| Fast dataframes | Polars | high-speed transforms |
| Charts | TradingView Lightweight Charts, Apache ECharts, uPlot | financial charts |
| Tables | AG Grid Community | scanner grid |
| NSE adapters | nselib, jugaad-data, NseIndiaApi, nsepython | data adapters behind fallbacks |

Rules:

- verify license and maintenance before implementation
- keep every data library behind an adapter
- unofficial NSE adapters need fallbacks and freshness checks
- local Greeks must be labeled ESTIMATED
- backtests must be point-in-time and avoid lookahead bias

## 36. Updated Build Order With Safety

1. Backend skeleton: FastAPI, SQLite, settings, health endpoint.
2. Data pipelines: market data, events, options chain, cross-market drivers.
3. Screening engine: hard filters, causal score, operator blocks, trap detection.
4. Safety engine: daily loss circuit breaker, cooldowns, panic lock, revenge detector, safety journal.
5. Intraday radar: execution score, liquidity window, gap fade, expiry mode.
6. Frontend: Screen 0 to Screen 11, safety bar, panic lock, recovery screen.
7. Risk and journal: sizing, correlation, equity curve, replay, safety analytics.
8. Validation: stale data, no silent thresholds, expiry calendar, operator blocks, safety lock tests.

## 37. Confluence Engine Audit Merge

This section records the later audit that identified missing professional confirmation details.

The update is now mandatory for future implementation.

Files updated:

- `SCREENER_RULES.md`: core confluence engine rules.
- `DASHBOARD_EXPERIENCE_PLAN.md`: command bar and stock-card display.
- `ASSESSMENT_RADAR_UPGRADE_PLAN.md`: this audit record.
- `CONFLUENCE_ENGINE_UPGRADE_PLAN.md`: standalone future reference.

## 38. Audit Results Preserved

Status after audit:

| Point | Status Before Merge | Final Action |
| --- | --- | --- |
| OI quadrant logic | partial | add standalone named states |
| MWPL/F&O ban risk | missing | add reliability gate before OI |
| futures basis/cost of carry | missing | add basis layer |
| rollover data near expiry | partial | add expiry/rollover interpretation |
| options IV confirmation | partial | add IV + OI confluence |
| deal price anchor | missing | add live anchor monitoring |
| event AVWAP | partial | add AVWAP from event dates |
| smart-money quality grading | missing | classify ESOP, open-market, transfer, pledge, sale |
| volume quality metrics | partial | add trade count, average trade size, volume location |
| SLB borrow proxy | missing/unclear | add short-pressure proxy where available |
| participant-wise OI scope | needed clarification | label as index/regime context only |
| confluence truth table | missing | add named state machine |
| Screen 0 command bar | missing | add persistent command bar |
| emotional safety as gate | already added, now reinforced | keep as Layer 9 gate |
| FOMO lock after big gap | missing | add ATR-distance downgrade |
| supply overhang tracking | partial | track remaining seller holding and absorption |

## 39. New Named Output States

Required states after this audit:

- PRIORITY_RADAR
- READY
- WAIT
- WAIT_FOMO
- WAIT_EMOTIONAL
- WAIT_OI_UNRELIABLE
- WAIT_BASIS_CONFLICT
- WAIT_SUPPLY_OVERHANG
- REJECT
- SHORT_WATCH
- NO_TRADE
- LOCKED_NO_TRADE
- STOP_TRADING_NOW

These states replace simple score-only final output.

## 40. 10-Layer Engine After Audit

```text
Screen 0: Command Bar
Layer 0: Global Macro Gate
Layer 1: Market Regime Gate
Layer 2: Sector Gate
Layer 3: Stock Safety Filter
Layer 4: Smart Money Layer
Layer 5: OI + Volume + Basis Layer
Layer 6: Setup Identification
Layer 7A: Price Acceptance And Anchor Layer
Layer 8: Risk Engine
Layer 9: Emotional Safety Gate
Layer 10: Execution And Post-Entry
```

Layer 7A and Layer 9 are mandatory.

## 41. Confluence Matrix Requirement

The final decision must combine:

- smart money quality
- OI quadrant
- MWPL reliability
- futures basis
- rollover
- IV + options OI
- volume quality
- deal anchor
- event AVWAP
- supply overhang
- FOMO distance
- portfolio risk
- emotional safety

Minimum matrix examples:

| Condition | State |
| --- | --- |
| strong smart money + long build-up + institutional volume + rising premium + anchors accepted | PRIORITY_RADAR |
| bullish smart money + short covering only | READY with sustainability warning |
| bullish OI but MWPL above 90 percent | WAIT_OI_UNRELIABLE |
| bullish price/OI but negative falling basis | WAIT_BASIS_CONFLICT |
| price more than 1x ATR past ideal entry | WAIT_FOMO |
| motivated seller still owns large stake | WAIT_SUPPLY_OVERHANG |
| daily loss or safety lock active | LOCKED_NO_TRADE |

## 42. Future Implementation Rule

Future implementation must not simplify this audit into:

```text
score >= threshold = buy
```

The correct behavior is:

```text
named state + reason + evidence + conflict explanation + next valid action
```

No READY state is valid unless:

- hard gates pass
- MWPL allows OI interpretation
- price acceptance is valid
- risk is defined
- trader safety is GREEN
- no unresolved conflict requires WAIT
<!-- HISTORICAL_SOURCE_END path=backup_reference_20260705_162956/backup_assessment_radar_upgrade_plan.md sha256=3cabd769625986982bcb577b32d0cf09a20418c41dc89ec5b4408e355a6d9eb5 -->

<!-- HISTORICAL_SOURCE_BEGIN path=backup_reference_20260705_162956/backup_confluence_engine_upgrade_plan.md sha256=783d0c6175712bddb0d03985803ac146fecfac1902f9e4e0d1e56c07bb618ae9 lines=398 -->
# TrendForge Confluence Engine Upgrade Plan

This file exists so future implementation does not forget the professional confirmation layer.

It is a standalone reference for the Smart Money + OI + Volume + Basis + Price-Acceptance engine.

## 1. Purpose

TrendForge must not mark a stock important only because one signal is strong.

The final radar must answer:

```text
Did smart money act?
Was the signal high quality?
Did price accept the smart-money level?
Did volume confirm with institutional quality?
Did OI confirm the same direction?
Is OI reliable after MWPL and expiry checks?
Is futures basis supportive?
Are options IV/OI confirming or warning?
Is the trade late/FOMO?
Is there supply overhang?
Is the trader safe to act?
```

## 2. Pages Updated

This requirement is stored in:

- `SCREENER_RULES.md`: section 46.
- `DASHBOARD_EXPERIENCE_PLAN.md`: sections 46 to 63.
- `ASSESSMENT_RADAR_UPGRADE_PLAN.md`: sections 37 to 42.
- `CONFLUENCE_ENGINE_UPGRADE_PLAN.md`: this standalone file.

## 3. What Was Missing Before

The audit found these missing or partial items:

- OI quadrant was partial, not a named per-stock state.
- MWPL proximity was missing before OI interpretation.
- Futures basis and cost of carry were missing.
- Rollover interpretation was mentioned but not built.
- IV rank existed, but IV + OI behavior was missing.
- Deal price anchor was missing.
- Event AVWAP was not built as a mechanism.
- Smart-money quality grading was missing.
- Volume quality metrics were partial.
- SLB borrow proxy was missing.
- Participant-wise OI scope needed clarification.
- Conflict matrix was missing.
- Screen 0 command bar needed to be persistent.
- Emotional safety needed to remain a gate before execution.
- FOMO lock after overextended move was missing.
- Supply overhang tracking was partial.

## 4. 10-Layer Decision Engine

```text
Screen 0: Command Bar
Layer 0: Global Macro Gate
Layer 1: Market Regime Gate
Layer 2: Sector Gate
Layer 3: Stock Safety Filter
Layer 4: Smart Money Layer
Layer 5: OI + Volume + Basis Layer
Layer 6: Setup Identification
Layer 7A: Price Acceptance And Anchor Layer
Layer 8: Risk Engine
Layer 9: Emotional Safety Gate
Layer 10: Execution And Post-Entry
```

Layer 7A and Layer 9 are mandatory.

## 5. Screen 0 Command Bar

Always visible:

```text
System: GREEN
Regime: TRADEABLE BULLISH
India VIX: Normal
Breadth: 1.8:1 Positive
Expiry Mode: OFF
MWPL Watch: SAFE
Liquidity Window: ACTIVE
Trader Safety: GREEN
NO_TRADE Override: OFF
```

The Command Bar can downgrade every stock card.

## 6. OI Quadrant

| Price | OI | State | Meaning |
| --- | --- | --- | --- |
| up | up | LONG_BUILD_UP | fresh longs entering |
| up | down | SHORT_COVERING | shorts exiting |
| down | up | SHORT_BUILD_UP | fresh shorts entering |
| down | down | LONG_UNWINDING | longs exiting |

Rule:

- LONG_BUILD_UP is more sustainable than SHORT_COVERING.
- OI quadrant must be shown on every F&O stock card.

## 7. MWPL Reliability Gate

MWPL must be checked before OI.

| MWPL Usage | State | Action |
| ---: | --- | --- |
| below 80 percent | SAFE | normal OI interpretation |
| 80 to 90 percent | YELLOW | caution |
| 90 to 95 percent | ORANGE | OI unreliable |
| above 95 percent | RED/F&O BAN | do not trust fresh OI signal |

State:

```text
WAIT_OI_UNRELIABLE
```

## 8. Futures Basis / Cost Of Carry

```text
basis = futures_price - spot_price
```

Strong confirmation:

```text
price up + OI up + basis premium rising = strongest long build-up
```

Conflict:

```text
price up + OI up + basis discount/falling = WAIT_BASIS_CONFLICT
```

## 9. Rollover Logic

Near expiry:

| Current Expiry OI | Next Expiry OI | Read |
| --- | --- | --- |
| falling | rising | position carried forward |
| falling | flat/down | position closing |
| rising | rising | aggressive late build-up |
| falling fast | not checked | do not interpret until rollover checked |

Expiry Mode changes OI interpretation.

## 10. IV + OI Confluence

| Options Behavior | State |
| --- | --- |
| call buying + IV rising + call OI rising | DIRECTIONAL_CALL_BUYING |
| put buying + IV rising + put OI rising | PUT_BUYING_PRESSURE |
| OI rising + IV falling | WRITING_PINNING |
| IV spike both sides | EVENT_FEAR_STRADDLE |
| high IV before event | IV_CRUSH_WARNING |

IV rank alone is not enough.

## 11. Deal Price Anchor

Every important transaction creates an anchor.

Anchor examples:

- FII bulk deal price
- MF block deal price
- CEO/promoter open-market buy price
- promoter/PE/co-founder sale price
- result-day anchor
- breakout trigger

States:

- ANCHOR_ACCEPTED
- ANCHOR_TEST
- ANCHOR_BROKEN

If a bullish deal anchor breaks with rising sell volume, downgrade or reject.

## 12. Event AVWAP

Track AVWAP from:

- insider buy date
- bulk/block deal date
- result day
- breakout day
- policy/order announcement day
- large sale day

Price above multiple event AVWAPs improves conviction.

Price below event AVWAP warns that the event is rejected.

## 13. Smart-Money Quality Grading

| Signal | Grade |
| --- | --- |
| CEO/promoter open-market buy | very strong |
| repeated promoter buys | very strong |
| FII/MF bulk deal at premium | very strong |
| high-quality block deal at market | medium/strong |
| token director buy | low |
| ESOP exercise/allotment | neutral |
| inter-se transfer | neutral |
| pledge release | positive |
| pledge addition | danger |
| promoter/PE/co-founder sale at discount | hard caution |

Do not score ESOP as open-market conviction.

## 14. Volume Quality

Required fields:

- RVOL-TOD
- traded value
- delivery percent with T+1 label
- bid-ask spread
- trade count
- average trade size
- average trade size change
- volume above/below VWAP
- volume near high/low
- candle close location
- spread-adjusted volume

Same raw volume can mean retail churn or institutional footprint. The system must distinguish it.

## 15. SLB Borrow Proxy

Use NSE SLB data where available as a short-pressure proxy.

Fields:

- borrow quantity
- lend quantity
- borrow rate
- rate change
- data freshness

High borrow rate plus breakout can mean squeeze potential.

If unavailable, show unavailable. Do not invent short interest.

## 16. Participant-Wise OI Scope

Participant-wise OI is index/regime context only.

Correct display:

```text
Participant OI: index/regime signal
Stock-level FII evidence: bulk deals, filings, FPI changes, delivery/RVOL proxy
```

Never claim participant OI proves FII buying in one stock.

## 17. Supply Overhang

Track large seller risk:

- seller identity
- seller type
- quantity/value sold
- remaining holding
- sale anchor price
- time since sale
- absorption evidence

States:

- SUPPLY_OVERHANG_HIGH
- SUPPLY_ABSORBED
- SUPPLY_REJECTION

If a motivated seller still owns more than 10 percent after a large sale, show supply risk until absorption is proven.

## 18. FOMO Lock

```text
if current_price > ideal_entry + 1x ATR:
    state = WAIT_FOMO
```

Output:

```text
WAIT_FOMO
Reason: price is too far past ideal entry.
Action: wait for VWAP retest, pullback, or next setup.
```

## 19. Final State Machine

Allowed final states:

- PRIORITY_RADAR
- READY
- WAIT
- WAIT_FOMO
- WAIT_EMOTIONAL
- WAIT_OI_UNRELIABLE
- WAIT_BASIS_CONFLICT
- WAIT_SUPPLY_OVERHANG
- REJECT
- SHORT_WATCH
- NO_TRADE
- LOCKED_NO_TRADE
- STOP_TRADING_NOW

The output must be a named state with reason, evidence, conflict explanation, and next action.

## 20. Confluence Matrix

| Smart Money | OI | Volume | Basis | Price Acceptance | State |
| --- | --- | --- | --- | --- | --- |
| strong | LONG_BUILD_UP | institutional | premium rising | above anchors | PRIORITY_RADAR |
| strong | SHORT_COVERING | strong | flat | above AVWAP | READY with sustainability warning |
| medium | LONG_BUILD_UP | decent | flat | above anchor | READY or WAIT |
| strong | LONG_BUILD_UP | weak | premium rising | too far past entry | WAIT_FOMO |
| strong | LONG_BUILD_UP | strong | negative/falling | below AVWAP | WAIT_BASIS_CONFLICT |
| weak ESOP only | LONG_BUILD_UP | high raw volume | premium | above anchor | WAIT |
| strong | any | any | any | MWPL above 90 percent | WAIT_OI_UNRELIABLE |
| bearish seller at discount | SHORT_BUILD_UP | high volume | discount | below anchor | REJECT or SHORT_WATCH |
| any | any | any | any | safety lock active | LOCKED_NO_TRADE |

## 21. F&O Versus Non-F&O Rule

F&O stocks:

- use OI, MWPL, futures basis, IV, options flow, rollover.

Non-F&O stocks:

- do not fake OI.
- use smart money, cash volume, delivery, AVWAP, anchors, supply, risk, and safety.

## 22. Data Storage Needed

Required tables:

- derivatives_oi_snapshots
- futures_basis_snapshots
- mwpl_snapshots
- rollover_snapshots
- iv_snapshots
- deal_anchors
- avwap_anchors
- volume_quality_snapshots
- slb_snapshots
- supply_overhang_events
- confluence_states

## 23. Testing Needed

Test:

- OI quadrant classification
- MWPL downgrade
- F&O ban block
- basis conflict
- rollover interpretation
- IV + OI flow type
- deal anchor accepted/broken
- AVWAP reclaim/rejection
- ESOP versus open-market buy
- trade count and average trade size
- SLB unavailable behavior
- participant OI scope
- WAIT_FOMO
- supply overhang
- LOCKED_NO_TRADE override

## 24. Implementation Principle

Never reduce this engine to:

```text
score >= threshold = buy
```

Correct final behavior:

```text
named state + evidence + conflict + next valid action
```

Capital protection and confirmation quality come before opportunity.
<!-- HISTORICAL_SOURCE_END path=backup_reference_20260705_162956/backup_confluence_engine_upgrade_plan.md sha256=783d0c6175712bddb0d03985803ac146fecfac1902f9e4e0d1e56c07bb618ae9 -->

<!-- HISTORICAL_SOURCE_BEGIN path=backup_reference_20260705_162956/backup_build_bible_gap_analysis.md sha256=83ff1bdb343f7a21ff9fbfafbb9ae1486c1065bdaebb93a4e46d164bcfd19429 lines=110 -->
# TrendForge Build Bible Gap Analysis

## Verification

Read and checked the attached Build Bible in these numbered ranges:

- lines 1-85: philosophy, causal framework, actor model, independence logic
- lines 86-170: data sources, fallback design, SQLite schema, data health, orchestrator order
- lines 171-255: macro, regime, sector, tradability, cause scoring
- lines 256-340: sponsor decay, Wyckoff, structure, flow, GEX, independence, trap gates, WHY generator
- lines 341-425: risk, slippage, portfolio correlation, exits, options depth, setup parameters, failure modes
- lines 426-503: remaining failure modes, skip-list, file plan, tests, daily workflow, start requirements

## What Was Already In The Old Plan

The old plan already had:

- NSE-first screener purpose
- 4-layer CAUSE/SPONSOR/STRUCTURE/FLOW scoring
- gated runtime sequence from macro to exit
- GIFT Nifty, FII/DII, sector, VIX, breadth, and options confirmation
- tradability filters like ASM/GSM, F&O ban, pledge, liquidity, market cap
- setup families: gap-and-go, ORB, VCP, 21 EMA pullback, PEAD, true relative strength
- RVOL-TOD, MTF, VWAP, OI, trap detection
- risk, position sizing, slippage, journal, backtest, dashboard, alerts

## What Was Missing Or Too Weak

The Build Bible added these missing or sharper rules:

1. Forced-counterparty analysis: every pick must ask who is forced to buy/sell and whether the trader is becoming the fuel.
2. Four trend causes: information asymmetry, forced flow, fundamental re-rating, reflexivity.
3. Six actor model: FII, DII, promoter/insider, named super-investor, market maker/option writer, retail/operator.
4. Top-decile universe gate: pass 3/4 layers is not enough; candidate should rank in the top 10 percent of today�s universe.
5. Exact gate thresholds: total score >= 18, CAUSE >= 2, SPONSOR >= 4, STRUCTURE >= 2, FLOW >= 2.
6. Exact SQLite schema for point-in-time data and backtests.
7. Data health states: GREEN, AMBER, RED with visible degradation.
8. Explicit staleness decay formula and lambda values.
9. Wyckoff effort-vs-result algorithm for hidden absorption.
10. GEX formula and gamma flip logic.
11. Cross-market driver mapping as a formal confirmation layer.
12. Independence penalty formula.
13. Trap hard-gates that cannot be overridden by score.
14. Eleven trap types with names and detection logic.
15. Reasoning generator clauses with source/date evidence.
16. Half-Kelly risk adjustment and risk clamp.
17. Portfolio correlation using 60-day returns, sector risk cap, total open risk cap.
18. Options depth: IV term structure, IV skew/risk reversal, 0DTE/expiry dynamics, premium concentration.
19. Extra modules: intraday_microstructure, swing_extras, options_depth, event_preposition, crowding, shorting_asymmetry.
20. Testing plan for traps, staleness, independence, source fallback, and point-in-time correctness.

## Big-Player / Less-Common Radar Data Added

These are the highest-value items common traders usually do not model well:

- promoter SAST and insider disclosures
- pledge and pledge-release risk
- named buyer/seller from bulk/block deals
- AMFI monthly holding deltas across schemes
- FII/DII cash plus derivative positioning
- FII index futures long/short ratio
- delivery percent anomaly, not just volume
- Wyckoff absorption bars: high volume with low price progress
- GEX and gamma flip
- options premium concentration by strike
- IV skew and IV term structure
- index inclusion/exclusion and passive flow pressure
- short squeeze fuel and days-to-cover where available
- cross-market drivers like crude, copper, DXY, USD/INR, Nasdaq
- high-volume-node/supply-zone trap checks
- narrow-index divergence: Nifty up but breadth weak

## How This Improves The Scanning Radar

The radar improves in five ways:

1. Earlier detection: it looks for information asymmetry, sponsor footprints, and absorption before price indicators confirm.
2. Better trap avoidance: it rejects operator pumps, weak delivery gaps, priced-in news, HVN breakouts, VWAP failures, and narrow-index rallies.
3. Better market alignment: it blocks setups when macro, regime, sector, or breadth are hostile.
4. Better flow detection: it uses RVOL-TOD, OI change, gamma/GEX, IV/skew, and premium concentration instead of plain volume.
5. Better survivability: it sizes by regime, score, half-Kelly, slippage, correlation, sector risk, and total open risk.

## Conflict Found And Resolved

The Build Bible says funnel telemetry can auto-loosen thresholds if output is below 3 candidates and auto-tighten if output is above 8.

That conflicts with the safety rule: do not silently relax filters to force trades.

Final decision added to `SCREENER_RULES.md`:

- funnel telemetry can recommend threshold changes
- it can show strict/normal/exploratory profiles
- it cannot silently loosen actionable-mode rules
- any threshold change must be visible in the UI

## Claims To Verify Later Against Official Sources

The Build Bible includes specific current broker/regulatory claims. They are useful planning assumptions, but they must be verified before implementation:

- Upstox current REST/WebSocket limits
- Upstox option Greeks availability and instrument caps
- Angel One endpoint behavior and limits
- NSE current endpoint paths and anti-bot behavior
- current SEBI and broker rules for any future auto-order execution

Until those are verified, TrendForge stays read-only plus alerts.

## Final Judgment

The Build Bible does improve the plan. The original rules had the skeleton. This document adds the institutional radar, exact math, data model, trap taxonomy, options depth, and implementation/test detail needed to build it without guessing.
<!-- HISTORICAL_SOURCE_END path=backup_reference_20260705_162956/backup_build_bible_gap_analysis.md sha256=83ff1bdb343f7a21ff9fbfafbb9ae1486c1065bdaebb93a4e46d164bcfd19429 -->

# 2026-07-11 Source Integration Analysis - Audited Hybrid Decision

## Audit Evidence

- Input: `C:/Users/sakth/Downloads/TrendForge_Source_Integration_Analysis.md`
- Read in full: 1,552 lines and 10,957 words.
- Input SHA-256: `878b43c1d3485dce98bd4096103c010ac89090b502cb41ffd09722268a0648ae`.
- Compared against the live resolver, integrity boundary, parsers, persistence, gate readiness, tests, source registry and current database artifacts.

## Accepted And Built

1. Source-first immutable lineage remains mandatory: fetch, archive raw bytes, verify transport/container/schema, normalize, persist, then evaluate gates.
2. NSE F&O UDiFF remains the official EOD derivative authority. Its required schema now includes symbol, close, prior close, open interest and OI change. Missing fields return `WAIT_SCHEMA_MISMATCH`; zero is never invented.
3. Official `fo_secban.csv` is now parsed exactly. Ban symbols are hard symbol-level vetoes. The file is explicitly `FNO_BAN_ONLY` and cannot masquerade as MWPL percentage evidence.
4. G13 now returns `WAIT_MWPL_PERCENTAGES` when only ban evidence exists, and `BLOCKED_FNO_BAN` for a listed symbol.
5. NSE bulk deals and CFTC COT were fetched through the production pipeline, archived by hash, integrity checked, normalized and persisted.
6. CFTC freshness now respects publication lag: through Friday the prior Tuesday report remains current; from Saturday the current-week Tuesday is required.
7. OpenAlgo received a read-only localhost client for the documented history and option-chain POST contracts. Credentials remain environment-only; order routes do not exist.
8. Invalid guessed resolver URLs were removed. MCX remains fail-closed until a real official artifact contract is captured.

## Corrected Or Rejected Claims

- The analysis's UDiFF status was stale; the official 2026-07-10 artifact is already live verified.
- Guessed `MWPL_*.csv` paths returned 404 and were removed. They are not evidence.
- Guessed MCX bhavcopy paths returned HTML, not bhavcopy data, and were removed.
- NSE SLB report names are official, but a stable direct download path has not been proven. SLB stays pending.
- RBI is not the current primary USD/INR reference-rate publisher; FBIL took over publication in 2018. A synchronized broker/licensed USD/INR feed is required for executable MCX decisions.
- CFTC COT is delayed category-level positioning, not trader identity or intraday flow.
- Missing OI cannot be normalized to zero. Missing required derivative columns are a schema failure.
- Corrupt ZIP data cannot fall back to raw-byte parsing. The integrity gate blocks it before normalization.
- CFTC backtests must use release availability, not Tuesday report date alone.
- Proposed rollover, SLB-yield and supply-absorption thresholds are research hypotheses until calibrated point-in-time; they are not hard production truth.
- Duplicate raw bytes may be reused, but a parser must rerun when parser version or schema contract changes.

## Live Evidence Added

| Source | Artifact | Result | Decision Role |
|---|---|---|---|
| NSE F&O ban | `fo_secban.csv`, 55 bytes, SHA-256 `229d37ee91791870be1337f70ccf5eaa9dc8dae86107163ab516ebf49265a303` | 2026-07-13, `KAYNES`, integrity PASS | Hard veto only; MWPL percentage pending |
| NSE bulk deals | `bulk.csv`, 8,200 bytes, SHA-256 `ceb35ff252c1fdc03531d26a8fe4f773b55511786c2f0c21f629466204122816` | 2026-07-10, 89 rows, integrity PASS | G12 stock-level event/anchor evidence |
| CFTC disaggregated COT | 2026 ZIP, 1,306,533 bytes, SHA-256 `7733ce1d4ba953e96206f3e1393150734f871a231b9350262910de5b66252806` | 2026-07-07, 10 relevant rows, integrity PASS | Delayed MCX regime context only |

## Remaining Build Order

1. Capture and fixture-test the official MWPL percentage artifact contract.
2. Discover a stable official NSE SLB download contract from the All Reports workflow; archive the exact response and verify field semantics before scoring.
3. Capture a stable official MCX bhavcopy artifact and add an MCX exchange calendar.
4. Connect OpenAlgo after user configuration; validate intervals, master-contract date, timestamp monotonicity, quote freshness and broker reconciliation before enabling live gates.
5. Add synchronized USD/INR, option Greeks/IV, futures basis and rollover evidence. No derived field may use asynchronous quotes without timestamp tolerance checks.
6. Backfill point-in-time releases and calibrate all heuristic thresholds out of sample before promotion from research-only.

## Production Rule

```text
Official URL reachability is not evidence.
Only an immutable, schema-valid, source-dated, fresh, scope-correct artifact may affect a gate.
Ban-only, delayed-only, metadata-only, unofficial-only, stale or missing inputs never create READY.
```

# 2026-07-13 Source Inventory Audit And Clean-Data Normalization

TrendForge now has a deterministic, persistent audit for the complete 211-link
inventory. Each run records all rows and the inventory manifest hash, but only
explicitly selected IDs may use the network. Direct official artifacts are
attempted before landing-page HTML. CSV, JSON, ZIP, HTML tables and embedded
JSON are profiled and archived; unknown HTML remains metadata and never becomes
trading evidence.

The first new normalized sources are FRED `DFII10` real yields and `DTWEXBGS`
broad dollar index. Both have source-specific schemas, missing-value handling,
daily freshness contracts and local observation storage. Real yields parsed
fresh through 2026-07-09; the dollar series parsed through 2026-07-02 and was
correctly marked stale. They are delayed MCX context only.

The audit also proved clean official JSON contracts for BSE buybacks/takeovers
and NSE corporate actions/daily buybacks, and clean CSV candidates for NSE
participant OI and bulk deals. AMFI legacy download candidates returned 404;
BSE bhavcopy, WGC, MCX and NSE SLB landing pages did not expose a trusted clean
artifact in the bounded pilot. Those sources remain blocked rather than being
scraped into false evidence.

Detailed per-link results:
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S012`.

## 2026-07-13 Current Source Activation Truth

All 146 formerly pending official URLs have a recorded network result. Three
were converted into scoped, source-dated, hash-archived contracts: EIA weekly
petroleum, MCX EOD futures and NSE SLB open positions. CFTC COT and NSE F&O
were also refreshed through their existing official contracts.

- MCX bhavcopy confirms EOD futures OHLC, volume and OI. It does not supply
  live MCX, IV or Greeks.
- NSE SLB supplies outstanding borrowed quantity. It does not supply exact
  short interest or borrow yield from this artifact.
- EIA supplies delayed weekly inventory context. It does not supply a
  point-in-time consensus surprise.
- AMFI has a confirmed per-AMC disclosure directory, but actual AMC workbooks
  remain unnormalized and cannot yet prove stock-level sponsorship.

Future agents should start from
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S010`. Rows marked metadata,
schema pending, artifact pending, blocked or document-only remain fail-closed.

## 2026-07-13 AMFI Scheme-Wise Official API Activation

The AMFI scheme-wise page is a directory backed by the official
`/api/schemewisedisclosure-investment` endpoint, not a universal workbook.
TrendForge now extracts the published fund IDs and quarters, probes backward to
the newest populated quarter, fetches every listed fund with bounded
concurrency, records every attempt, hashes each response and archives one
complete source bundle.

Live verification accounted for all 56 funds: two returned 460 rows and 54
returned the official `Nil` no-data response. The normalized evidence date is
the quarter end, 2026-03-31. All 460 rows are persisted without collapsing
separate equity and futures legs.

This source provides market value and portfolio percentage, not quantity. It is
quarterly delayed swing context only. It does not create quantity deltas,
intraday buying claims, stock-symbol evidence or `READY`. ISIN-to-NSE-symbol
mapping remains a separate required validation step. AMFI monthly per-AMC
workbooks remain pending for true quantity changes.

Corrected source status is recorded in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S013`.

## 2026-07-13 Eight-Fetcher Verification

Two new official contracts were activated. `nse_fii_dii` stores two aggregate
cash-flow rows dated 2026-07-13 and is linked to the institutional-regime source
gate. `amfi_nav` stores 14,216 scheme NAV observations through 2026-07-12 and
is restricted to fund-pricing reference use.

The BSE bhavcopy, NSE option-chain, PIT and live block-deal endpoints are now
registered monitors. Empty JSON is shown as `NO_DATA_NOW`; BSE HTML is shown as
`WRONG_CONTENT_NOW`; one live block-deal context row is stored. These states
remain visible and are rechecked, but cannot confirm a trade until dated,
schema-valid rows exist.

Current registered-contract status: 18 fresh structured, one structured stale,
10 partial/metadata/empty/wrong-content and nine unconnected. Detailed results are in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S014`.

## 2026-07-13 Nine-Source Fetcher Integration

The submitted fetcher was verified against live source shapes and merged into
the existing source-first pipeline. Five source families were new: ASM, GSM,
promoter pledge, OI spurts and NSDL daily FPI trends. FII/DII, current PIT,
option chain and AMFI NAV already existed and were not duplicated.

- ASM/GSM are now a dedicated G03 stock-safety gate. Fresh official empty GSM
  is valid; a listed symbol is blocked.
- All 1,532 pledge rows are preserved. Stock-level use waits for point-in-time
  company-to-symbol/ISIN mapping.
- OI spurts provide 215 activity rows but cannot calculate MWPL utilization.
- NSDL provides 25 cash/debt and nine derivative aggregate rows, not stock-level
  FPI holdings.
- Empty current option-chain and PIT responses remain visible as `NO_DATA_NOW`
  and are checked again later; they are not rejected or converted into zeros.

Current source-family count is 43: 24 fresh structured, one stale structured,
nine partial/empty/metadata/wrong-content and nine unconnected. The canonical
saved-link inventory remains 211 URLs.

## 2026-07-13 Gold And China Physical Context

TrendForge now archives, parses and displays four additional official contracts:
WGC gold futures OI, WGC ETF holdings, WGC ETF flows and the SGE daily report.
Their current structured row counts are 1,256, 5,839, 2,225 and 17. LME
warehouse and MCX delivery contracts are visible but access-blocked.

These sources explain commodity regime and physical demand; they do not create
standalone trades. The MCX gate remains blocked until synchronized USD/INR is
available through OpenAlgo or another official/licensed source. This prevents
gold direction from being inferred from COMEX, ETF or SGE data while ignoring
the currency leg that determines the MCX price.

## 2026-07-13 Institutional Multi-Factor Engine

TrendForge now has a config-driven, read-only institutional research layer.
It preserves all 37 submitted NSE/BSE/AMFI/MFAPI/NSDL endpoint contracts in
`config/config.yaml`; 15 contracts point to existing canonical normalization
owners so raw fetches are not parsed twice or counted as independent evidence.

The live all-contract audit produced 20 `RAW_ARCHIVED`, six `NO_DATA_NOW`, nine
`BROKEN`, and two `WRONG_CONTENT` outcomes. Every successful HTTP body is
content-hash archived before parsing. Raw, empty, stale and wrong-content
responses cannot score. Exact rows are stored in
`TREND_FORGE_SOURCE_REGISTRY.md`, segment `S017`.

Implemented calculations include trend, momentum, volume, volatility and risk
features, historical VaR/CVaR, drawdown, factor weighting, deterministic risk
sizing for the INR 1 lakh account, and chronological walk-forward validation.
Isolation Forest is an anomaly veto, not a direction vote. HMM, Random Forest,
XGBoost and LSTM remain directional model contracts; no model can pass until a
trained, versioned and validated artifact exists.

The public API ignores caller-supplied `sourceReady` and `modelsReady` flags.
Therefore a bot cannot self-certify a `READY` result. Current output remains
`WAIT` until internal source/model artifact resolvers are completed. TrendForge
v1 remains read-only and does not place broker orders.

## 2026-07-14 Ten-Source Corporate Disclosure Fetch Group

TrendForge now exposes one bounded fetch group for ten NSE/BSE corporate and
ownership sources. It uses the existing async client, NSE homepage session
seed, exchange-specific headers, per-host rate limiting, SHA-256 immutable raw
archives, explicit empty states and stale fallback. The batch API is
`POST /api/institutional/corporate-sources/fetch` and requires an NSE symbol,
BSE scrip code and ISO date range.

Live verification replaced seven dead or inaccurate guidance URLs with current
exchange page contracts. Verified NSE paths are corporate announcements,
`corporate-share-holdings-master`, aggregate pledge data,
`corporate-shareholding-disclosure` for Regulations 29 and 31, current PIT and
daily buyback execution. Verified BSE paths are `AnnSubCategoryGetData`,
`InsiderTrade15` and `GetCorpPledgeShareholding_ng`.

The bounded RELIANCE / BSE 500325 run produced structured archived data for NSE
announcements (20), shareholding filings (90), pledge rows (1,532), Regulation
31 events (83), Regulation 29 events (45), BSE announcements (5) and BSE pledge
rows (1,242). NSE PIT, NSE daily buyback and BSE insider trading returned valid
empty JSON for the selected time window and remain visible as `NO_DATA_NOW`.

These are raw connection results, not scanner proof. `canScore` remains false
for every endpoint until source-specific normalization, source-date extraction,
freshness checks, revision/deduplication handling and symbol-scope validation
are complete. NSE daily buyback execution is not a substitute for tender-offer
terms; BSE/NSE offer sources remain the authority for offer-price evidence.

## 2026-07-14 Safety Recovery Dialog Fix

The recovery dialog previously allowed an incomplete checklist to reach
`POST /api/safety/unlock`. FastAPI correctly returned HTTP 422 because all five
recovery acknowledgements are mandatory, but the frontend discarded the API
validation detail and displayed only a generic status code. This made a valid
safety rejection look like a broken unlock function.

The frontend now validates all five acknowledgements and the minimum review
note before enabling `Request Unlock`. It loads active safety events, displays
the remaining manual-lock cooldown as a live countdown, and keeps the button
disabled until the cooldown expires. API 409/422 response details are now shown
to the user. The backend rules were not weakened: cooldown plus all five
acknowledgements remain mandatory.

Verification: the running server returns the updated versioned assets, Node
syntax validation passed, all 108 frontend acceptance checks passed, and all
five safety-engine tests passed. In-app browser automation could not attach in
this run, so no visual browser pass is claimed.

## 2026-07-14 Future Extension And GitHub Intake Plan Audit

Reviewed attachment:
`C:/Users/sakth/.codex/attachments/e0a3c8c7-8a2e-4ab5-953a-7aa02c3a680a/pasted-text-1.txt`
(678 lines, SHA-256
`27F372E9CB09942DF9B466D0C80B6521DA3F9D64A5E0E4A55609984E57A9B54C`).

Verdict: the plan's market logic, fail-closed source model, point-in-time
lineage, causal layers, harmonic safety rules, named states, risk controls and
validation requirements remain valid. The plan must not be executed unchanged
because several bootstrap assumptions are older than the current repository.

Required authority corrections:

- Replace the missing `TREND_FORGE_MASTER_PLAN.md` reference with the active
  authority set: `AGENTS.md`, the current sections of `present.md` including
  `16. Build Order`, `TREND_FORGE_ARCHITECTURE.md`, and
  `TREND_FORGE_SOURCE_REGISTRY.md`. Use the embedded historical implementation
  plan in `present.md` only for preserved milestone and acceptance evidence.
- Treat the dependency-free vanilla dashboard as an intentional established
  implementation. Do not rewrite it to React/Vite merely to match a fallback
  default intended for an empty repository.
- Preserve the existing SQLite migration ledger and direct typed storage layer.
  SQLAlchemy/Alembic migration is optional and requires measured benefit, a
  compatibility plan and complete data migration tests.
- Preserve the current calendar-aware scanner/source schedulers. APScheduler is
  optional; migrate only if durable job semantics or cron management justify
  the additional dependency.
- Use the installed compatible Python runtime rather than assuming Python 3.12.
  Every added dependency must be verified against Python 3.14.3.
- Keep TrendForge v1 read-only. A future OpenAlgo bot must consume a versioned,
  expiring, non-executable decision/intention contract through a separately
  authorized execution service. GitHub code may not directly place orders.
- Refresh `docs/BUILD_STATUS.md` and `docs/VALIDATION.md`; their headline dates
  and some test/source counts predate the latest 275-backend/108-frontend
  baseline and extended source work.

The current code is modular but not fully extension-ready. Source definitions
and OHLCV selection still use hardcoded `Literal` unions, authority maps and an
`if` dispatch chain. Adding many GitHub adapters directly to those branches
will create coupling and repeated edits. Before broad third-party integration,
add an explicit, allowlisted extension layer with these contracts:

1. `MarketDataAdapter`: canonical point-in-time OHLCV or market rows.
2. `EvidenceProvider`: typed CAUSE/SPONSOR/STRUCTURE/FLOW evidence with source,
   observed time, available time, freshness and correlation-family identity.
3. `SetupDetector`: setup candidates only; cannot emit READY or position size.
4. `FeatureProvider`: deterministic versioned features with no future data.
5. `RiskRule`: quantity-reducing or veto-only output; never increases quantity
   beyond the core risk engine result.
6. `UniverseProvider`: versioned symbol membership and effective dates.
7. `Exporter`: read-only decision/intention output for Trade Vision/OpenAlgo;
   no broker credentials or order methods inside an analytical extension.

Every extension requires a checked-in manifest containing extension ID,
capability, repository URL, pinned commit/tag, artifact hash, license and
notices, dependency versions, Python compatibility, network hosts, data trust,
input/output schema versions, timeframes, expected latency, failure state,
feature/evidence correlation family and `can_unlock_ready=false` by default.
Registration must be explicit and allowlisted; never import arbitrary Python
files or install a GitHub repository from a frontend request.

GitHub intake gate:

1. Record repository URL, exact commit and intended function.
2. Review upstream license plus packaged license; reject incompatible or
   ambiguous code from the core. GPL/NOC code remains isolated or reference
   only unless separately approved.
3. Review secrets, subprocesses, filesystem writes, dynamic imports, telemetry,
   network destinations and unsafe deserialization.
4. Pin dependencies and generate a reproducible lock/SBOM record.
5. Build an adapter around the project; do not copy its business logic into
   scanner gates without an independent TrendForge validator.
6. Validate canonical schema, timestamp timezone, market/session rules,
   corporate-action behavior, missing/stale/duplicate records and bounded
   resource use.
7. Run golden fixtures, malformed-input tests, point-in-time/lookahead tests,
   deterministic reruns, performance benchmarks and comparison against the
   existing implementation.
8. Persist raw input, extension version, normalized output and decision lineage.
9. Keep the extension in research-only mode until sample size, false-positive
   rate, expectancy, drawdown and failure behavior meet explicit promotion
   thresholds.
10. Require core gates to confirm any extension result. No GitHub detector,
    indicator, model or scanner may independently unlock READY.

For future stock-screening search, implement a query over normalized, versioned
feature and decision tables rather than fetching websites during each search.
The pipeline should remain:

`universe -> data health -> cheap liquidity prefilter -> cached features ->`
`causal gates -> setup detectors -> expensive intraday/harmonic checks -> risk`
`and safety -> rank -> persisted explanation`.

Add feature identity using `(symbol, timeframe, as_of, feature_key,
feature_version, input_hash)` and index the latest eligible rows by universe,
state, timeframe, sector and score. This permits new GitHub-derived features to
be added without rewriting the search UI or corrupting historical ML labels.

Current promotion blockers remain: licensed/live intraday truth for production
execution, normalized/fresh parsers for newly raw-archived sources, calibrated
and persisted model artifacts, all-universe performance evidence, and a
separately authorized OpenAlgo execution contract. The architecture is suitable
for continued feature additions after the extension registry and GitHub intake
gate above are implemented.

## 2026-07-14 Combined Pre-Open, Derivatives, Beta And OpenAlgo Plan

This is an additive extension of the existing TrendForge plan. It does not
remove or weaken the official-source archive, G00-G14 gates, harmonic engine,
smart-money/OI checks, deterministic risk sizing, emotional lock, ML lineage or
WAIT/REJECT behavior.

### Current Verified State

| Capability | State | Authority |
| --- | --- | --- |
| OpenAlgo `/api/v1/history` | Implemented read-only client | Broker/OpenAlgo after user credentials |
| OpenAlgo `/api/v1/optionchain` | Implemented read-only client | Broker/OpenAlgo after user credentials |
| OpenAlgo `/api/v1/optiongreeks` | Implemented and contract-tested | Black-76 result from OpenAlgo |
| OpenAlgo `/api/v1/multioptiongreeks` | Implemented and contract-tested, 1-50 contracts | Black-76 result from OpenAlgo |
| OpenAlgo `/api/v1/oi-analytics` | Proposed, not exposed | Must be added and verified in OpenAlgo |
| OpenAlgo `/api/v1/gex` | Proposed, not exposed | Must be added and verified in OpenAlgo |
| PCR / Max Pain / OI walls | Existing plan and partial math only | TrendForge calculation from archived option chain |
| `GEX_PROXY` | Planned | TrendForge calculation with limitation label |
| Rolling beta | Planned | TrendForge `statsmodels.RollingOLS` calculation |
| Pre-open state lifecycle | Planned | Official NSE snapshots plus post-open confirmation |
| OpenAlgo order execution | Not implemented | Separate future authorization and kill switch |

Focused verification completed after the client change:

```text
backend/tests/test_openalgo_client.py: 8 passed
backend/trendforge_api/openalgo_client.py: py_compile passed
```

The OpenAlgo client intentionally has no order methods. Its route-status map
marks `optionchain`, `optiongreeks` and `multioptiongreeks` as
`VERIFIED_READ_ONLY`; proposed OI/GEX wrappers are
`PROPOSED_NOT_EXPOSED`. OpenAlgo's logged-in OI-tracker/GEX web pages are not
treated as stable API-key contracts.

### Official Pre-Open Data Contract

Source family:

```text
https://www.nseindia.com/api/market-data-pre-open?key=NIFTY
https://www.nseindia.com/api/market-data-pre-open?key=FO
https://www.nseindia.com/api/market-data-pre-open?key=SME
```

Every request uses the existing NSE homepage seed/session, bounded retries,
rate limits, immutable raw archive and source timestamps. The exchange-calendar
schedule in `Asia/Kolkata` is:

```text
08:58     seed session and verify trading day
09:00:30  opening snapshot
09:04:30  developing auction snapshot
09:07:00  stabilization snapshot
09:08:30  final auction snapshot when published
09:14:30  freeze pre-open evidence and create watch candidates
09:15+    confirm with fresh first-5m and first-15m evidence
```

Normalized fields:

```text
category, symbol, series, purpose
source_timestamp, retrieved_at, snapshot_sequence
indicative_equilibrium_price, previous_close
final_price, final_quantity, total_turnover
total_buy_quantity, total_sell_quantity
ato_buy_quantity, ato_sell_quantity
market_cap, raw_snapshot_id, content_hash
```

Versioned calculations:

```text
gap_pct = (IEP - previous_close) / previous_close * 100
order_imbalance = (buy_qty - sell_qty) / (buy_qty + sell_qty)
ato_imbalance = (ato_buy_qty - ato_sell_qty) / (ato_buy_qty + ato_sell_qty)
matched_notional = IEP * matched_quantity
IEP stability = dispersion and direction changes across archived snapshots
auction quality = completeness + match ratio + IEP stability + market breadth
```

Zero denominators and missing snapshots return UNKNOWN. No interpolation or
carry-forward is allowed. The required lifecycle is:

```text
PREOPEN_WATCH
  -> OPEN_CONFIRMATION_WAIT
  -> READY / WAIT / REJECT
```

`PREOPEN_WATCH` is not executable. READY requires fresh post-open price,
volume, RVOL-TOD, VWAP, spread/depth and market/sector confirmation plus every
existing hard source, risk and safety gate. All WATCH, WAIT, REJECT and READY
states are saved for future outcome analysis.

### Derivatives And Beta Contract

The symbol-level derivatives pipeline is:

```text
OpenAlgo option chain + batch Greeks
  -> archived contract rows
  -> expiry/symbol/time validation
  -> PCR, Max Pain, walls, IV term/skew and GEX_PROXY
official futures bhavcopy + MWPL/ban + spot
  -> OI quadrant, basis and rollover reliability
RollingOLS(symbol returns, benchmark returns)
  -> beta, alpha, correlation, residual volatility and observation quality
all evidence -> existing G13, risk and scanner state machine
```

Required derivative lineage includes symbol, instrument token/contract,
exchange, expiry, strike, option type, observed time, available time, source
cutoff, source authority, raw artifact, model name/input, calculation version
and freshness. Batch Greeks are chunked to 50 contracts. Partial failures are
stored per contract and cannot disappear inside an aggregate success state.

PCR, Max Pain and OI concentration identify positioning and possible pin/wall
areas; they do not identify the trader. Public option OI also does not reveal
dealer long/short inventory. Therefore gamma exposure is always called
`GEX_PROXY` and is used only as FLOW/risk context, never as standalone proof or
a READY trigger.

Beta design:

```text
engine: statsmodels.RollingOLS
windows: configurable 60 / 120 / 252 completed sessions
benchmarks: NIFTY 50 or effective sector/index mapping
stored: beta, alpha, correlation, residual volatility, observations,
        benchmark, source cutoff, corporate-action version, calculation version
```

Insufficient observations, stale candles, an unadjusted corporate action or low
benchmark correlation produce UNKNOWN and a quantity reduction/WAIT. The
scanner never substitutes beta 1.0 merely to complete a score.

### Open-Source And License Decisions

- `statsmodels` is the preferred beta implementation; do not hand-roll rolling
  regression unless performance evidence requires it.
- TrendForge keeps its tested deterministic option math as an independent
  validator. OpenAlgo supplies live Black-76 values when configured.
- QuantLib may be added as a fixture/reference oracle for difficult IV/Greek
  cases. It does not become a direction engine.
- `py_vollib` remains optional/reference-only because current Python runtime
  compatibility and maintenance must be reverified before installation.
- OpenAlgo is AGPL-licensed and remains a separate localhost service. TrendForge
  consumes documented APIs and does not copy OpenAlgo service code into its
  process.
- Unofficial GitHub NSE wrappers can be fallback/reference adapters only. They
  cannot replace official pre-open evidence or unlock READY.

Reference links:

- OpenAlgo: https://github.com/marketcalls/openalgo
- OpenAlgo features: https://openalgo.in/features
- statsmodels RollingOLS: https://www.statsmodels.org/stable/generated/statsmodels.regression.rolling.RollingOLS.html
- QuantLib Python: https://github.com/lballabio/QuantLib-SWIG
- py_vollib: https://github.com/vollib/py_vollib
- NSE Python wrapper: https://github.com/aeron7/nsepython
- PKScreener: https://github.com/pkjmesra/PKScreener
- NseKit: https://pypi.org/project/NseKit/
- stock-nse-india: https://github.com/hi-imcodeman/stock-nse-india
- NSE pre-open archive reference: https://github.com/tkanhe/NSE-India-PreOpen-Market-Data
- NSE-Stock-Scanner reference: https://github.com/deshwalmahesh/NSE-Stock-Scanner
- Indian-Stock-Market-API reference: https://github.com/0xramm/Indian-Stock-Market-API
- NSEpy historical reference: https://github.com/swapniljariwala/nsepy

### Combined Implementation Order

1. Persist the five official pre-open snapshots with raw lineage and strict
   missing/duplicate/stale handling.
2. Build IEP stability, imbalance, matched-notional and auction-quality
   features with deterministic fixtures.
3. Add lifecycle transitions and UI states without permitting pre-open READY.
4. Persist verified OpenAlgo option-chain, single-Greeks and batch-Greeks
   responses; live-test only after user credentials are supplied.
5. Implement point-in-time PCR, Max Pain, walls, IV/skew and `GEX_PROXY` from
   archived rows.
6. Implement RollingOLS beta/correlation and corporate-action quality gates.
7. Wire symbol-level derivatives/pre-open evidence into existing G13, risk and
   scanner explanations.
8. Add OpenAlgo `/api/v1/oi-analytics` and `/api/v1/gex` wrappers in the
   OpenAlgo service, then verify their schemas before changing route status.
9. Run holiday, incomplete-auction, stale quote, duplicate/revision, expiry
   mismatch, zero/missing OI, bad IV, partial batch failure, low-history beta,
   low-correlation beta, timeout, rate-limit, load and lookahead tests.
10. Run research-only shadow scans and backtests. Keep execution disabled until
    broker mappings, risk revalidation, idempotency and kill-switch tests are
    separately approved.

## Consolidated Master Topic Index - 2026-07-14

This index is the navigation entry for the consolidated `present.md`. Existing
lines above remain unchanged. Embedded source files below are verbatim copies
with original line counts, byte counts and SHA-256 hashes. Historical text is
evidence; later explicit current-status sections control when statements
conflict.

### Topic Directory

| Required topic | Primary section or search phrase |
| --- | --- |
| Product purpose, user and scope | `Confirmed Product Intent` |
| Account risk and quantity | `Non-Negotiable Risk Rule`, `Preferred Account Risk Defaults` |
| Emotional safety and trade locks | `Emotional Safety Defaults`, `Trader Safety And Emotional Emergency Layer` |
| NSE/MCX universe | `Universe Policy`, `MCX Engine` |
| OpenAlgo contract and limitations | `OpenAlgo Bot Contract`, `Combined Pre-Open, Derivatives, Beta And OpenAlgo Plan` |
| Data retention and ML history | `Data Retention Defaults`, `Research, ML And Backtest` |
| Scanner timing and completion | `Scan Completion Targets`, `Daily Workflow Rules` |
| Stale, missing and failed data | `Failure And Stale-Data Policy`, `Source And Link Coverage Truth` |
| Promotion/backtest standards | `Backtest And Promotion Standard` |
| Source/parser/model rollback | `Parser And Model Rollback Policy` |
| Current implementation truth | `Verified Present Runtime State`, `Current Source Activation Truth` |
| Source links and API authority | See `TREND_FORGE_SOURCE_REGISTRY.md` |
| Architecture and graphs | See `TREND_FORGE_ARCHITECTURE.md` |
| Full scanner and gate logic | `TrendForge Screener Rules, Purpose, Logic, And Reason` |
| Smart money and institutional evidence | `Smart Money, OI, Volume, Basis, And Price-Acceptance Confluence Engine` |
| NSE volume, most-active and live large-deal watch | `NSE Market Activity Watch Integration - 2026-07-14` |
| Current 215-link reconciliation and commodity adapters | `Priority Source Adapter Completion - 2026-07-15` |
| Corporate, ownership, pledge, SAST and deal normalization | `Verified Disclosure Intelligence Normalization - 2026-07-14` |
| Harmonic patterns | Search `Harmonic` and use architecture/implementation sections |
| OI, MWPL, basis, rollover and IV | `TrendForge Confluence Engine Upgrade Plan` |
| Pre-open lifecycle | `Combined Pre-Open, Derivatives, Beta And OpenAlgo Plan` |
| Options, Greeks, GEX_PROXY and beta | `Derivatives And Beta Contract` |
| Frontend and dashboard behavior | `Hybrid Dashboard Experience And Output Plan` |
| Safety recovery dialog | `Safety Recovery Dialog Fix` |
| GitHub/open-source intake | `Future Extension And GitHub Intake Plan Audit` |
| Installation, startup and API routes | `EMBEDDED SOURCE: README.md` |
| Review findings and known risks | `EMBEDDED SOURCE: REVIEW.md` |
| Milestones, tests and acceptance gates | `EMBEDDED SOURCE: TREND_FORGE_IMPLEMENTATION_PLAN.md` |

### Consolidated File Roles

| Root document | Active responsibility |
| --- | --- |
| `AGENTS.md` | Automatically discovered engineering and safety rules |
| `present.md` | Product truth, current status, trading rules, setup, reviews and implementation plan |
| `TREND_FORGE_ARCHITECTURE.md` | Architecture, graphs, schemas, module/folder boundaries and integrations |
| `TREND_FORGE_SOURCE_REGISTRY.md` | Complete source/link/API inventory, contracts, freshness and parser status |

### Embedded Source Directory

| Stable search label | Original file | Purpose |
| --- | --- | --- |
| `EMBEDDED SOURCE: README.md` | `README.md` | Setup, run commands, routes and operational introduction |
| `EMBEDDED SOURCE: REVIEW.md` | `REVIEW.md` | Reviews, risks, gaps and security findings |
| `EMBEDDED SOURCE: TREND_FORGE_IMPLEMENTATION_PLAN.md` | `TREND_FORGE_IMPLEMENTATION_PLAN.md` | Complete milestones, tests, failure cases and acceptance gates |

The unchanged originals are retained under
`delete/top_level_md_consolidation_2026-07-14/`. The machine-readable
`documentation_consolidation_manifest.json` records every original path,
archive path, content hash and embedded boundary.


<!-- CONSOLIDATED_SOURCE_BEGIN
label: README
original_path: README.md
line_count: 197
byte_count: 8463
sha256: ED58DFF72D2C1663BF50BCF365F304E3365E654ACC3026A073D19C013DD92874
copy_mode: VERBATIM_BYTES
-->
<a id="embedded-source-readme"></a>

## EMBEDDED SOURCE: README.md

# TrendForge

TrendForge is a local, read-only Indian-market research command center. It archives source evidence, validates data health, scans stored candles, evaluates guarded setup/risk logic, and persists research outcomes. It does not place, modify, or cancel broker orders.

## Current State

The current application is a guarded research prototype. Deterministic fixtures and unofficial adapters support development, while missing or stale official evidence blocks executable `READY`. OpenAlgo is not connected.

Authoritative project documents:

- `present.md` - current product requirements and safety boundary;
- `TREND_FORGE_ARCHITECTURE.md` - target and implemented architecture;
- `TREND_FORGE_IMPLEMENTATION_PLAN.md` - milestone and data-to-decision build plan;
- `TREND_FORGE_SOURCE_REGISTRY.md` - source authority, links and integration rules.

The original merged master plan is preserved at `archive_markdown_backup_20260710/TREND_FORGE_MASTER_PLAN.md.backup` and embedded verbatim in the canonical documents. Its SHA-256 is `978939b64e3a39f1329e0c19c3c059e3f253bb53b9080d4fa3c107b10d44dc2d`.

## Prerequisites

- Python 3.12 or newer compatible Python;
- Node.js for the frontend acceptance checks;
- no broker credentials or network access for tests/demo research mode.

## Install

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
```

POSIX shell:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

Optional local model research dependencies are isolated from the core server:

```powershell
python -m pip install -r backend\requirements-ai.txt
```

Installing a model package does not make a model production-ready. A trained,
versioned, point-in-time validated artifact is still required before its output
can unlock a decision gate.

## Run

```powershell
cd backend
python run_server.py
```

Open `http://127.0.0.1:8000/`. API documentation is at `http://127.0.0.1:8000/docs`.

Initialize storage and load deterministic offline research data:

```powershell
cd backend
python -m trendforge_api.cli init-db
python -m trendforge_api.cli migrate
python -m trendforge_api.cli source-coverage
python -m trendforge_api.cli benchmark-nifty50
python -m trendforge_api.cli demo-data --symbol TFDEMO
python -m trendforge_api.cli demo-decisions
python -m trendforge_api.cli demo-harmonic-lifecycle
```

The candle demo creates daily and five-minute NSE-session candles in SQLite and Parquet. The decision demo persists eight explicit READY/WAIT/REJECT/NO_TRADE/stale/FOMO/safety scenarios for end-to-end UI validation. They are permanently labeled `SYNTHETIC_TEST`, `executable=false` and cannot authorize broker execution.

The benchmark command runs the complete cached scanner path over exactly 50
official-current Nifty 50 members. Its deterministic candles are labeled
`SYNTHETIC_TEST`, and the benchmark can never create executable output.

Build any supported derived timeframe from one stored source series:

```text
POST /api/nse/resample
query: symbol, source, sourceTimeframe, targetTimeframe, persist
targets: 30m, 1h, 4h_custom, 1d, 1w
```

Every derived candle carries `barState`, `sessionDate`, and `completeness`. The final 15-minute 30m/1h bucket and 135-minute custom-4h afternoon bucket are explicitly `PARTIAL_NSE_SESSION`.

## Validate

```powershell
cd backend
python -m pytest -q
python -m ruff check trendforge_api tests
python -m ruff format --check trendforge_api tests
python -m mypy trendforge_api --ignore-missing-imports
python -m compileall -q trendforge_api tests
cd ..\frontend
npm test
```

Persistence initialization is idempotent and versioned in `schema_migrations`. Run `python -m trendforge_api.cli migrate` after updating the application and inspect `GET /api/storage/migrations` before trusting a new build.

## Important Routes

```text
GET  /api/health
GET  /api/storage/migrations
GET  /api/storage/candle-quality
GET  /api/storage/candle-revisions
GET  /api/storage/candle-adjustments
POST /api/storage/candle-adjustments/reconcile
GET  /api/corporate-actions/{symbol}/reconciliation
POST /api/bse-offers/xbrl/refresh
GET  /api/bse-offers/xbrl/documents
GET  /api/bse-offers/events
GET  /api/evidence/{symbol}
GET  /api/source-health
GET  /api/source-monitor/catalog
GET  /api/source-contracts/coverage
POST /api/source-inventory/audit
GET  /api/source-inventory/audit-runs
GET  /api/source-inventory/audit-rows
GET  /api/gates/readiness
POST /api/scanner/run-once
GET  /api/scanner/latest
GET  /api/scanner/candidates
GET  /api/shortlist
GET  /api/wait-candidates
GET  /api/rejected-candidates
POST /api/causal/evaluate
POST /api/demo/decision-scenarios/load
POST /api/harmonic/scan
GET  /api/harmonic/patterns
POST /api/harmonic/lifecycle/evaluate
GET  /api/harmonic/lifecycle/events
GET  /api/alerts
POST /api/alerts
GET  /api/journal
POST /api/journal
GET  /api/settings/risk
GET  /api/universe/status
GET  /api/universe/instruments
POST /api/context/market/evaluate
GET  /api/context/market/latest
GET  /api/context/official/status
POST /api/context/official/backfill
POST /api/context/official/rebuild
POST /api/context/sector/evaluate
GET  /api/context/sector/latest
GET  /api/safety/status
GET  /api/safety/events
POST /api/safety/panic-lock
POST /api/safety/unlock
GET  /api/institutional/config
GET  /api/institutional/sources
GET  /api/institutional/models
POST /api/institutional/sources/fetch
POST /api/institutional/features
POST /api/institutional/analyze
POST /api/institutional/screen
GET  /api/institutional/reports
POST /api/institutional/backtest
```

The institutional endpoints are config-driven in `config/config.yaml`. Run a
bounded raw-source audit with:

```powershell
cd backend
python -m tools.audit_institutional_endpoints
```

Raw responses are content-hash archived and remain non-scoreable until an
endpoint-specific parser validates schema, source date, scope and freshness.
The public analysis API also ignores caller-supplied readiness flags; readiness
must eventually come from persisted source and model artifacts inside
TrendForge.

## Data And Safety

- SQLite stores metadata, source artifacts, parser/gate records, scanner results, settings and research records.
- Parquet stores larger candle datasets.
- Raw source artifacts are content-addressed under `data/raw_sources`.
- yfinance, nselib, nsepython and openchart remain unofficial/research-only according to their source contracts.
- Source URL presence is not evidence. A gate requires a current raw artifact, matching structured parse, correct scope, freshness and symbol evidence.
- The official NSE equity master and Nifty 500 constituent files populate a point-in-time instrument/industry universe. Market regime still requires a separate dated Nifty, India VIX and breadth context snapshot.
- Official market context uses archived NSE CM UDiFF bhavcopy and all-indices close files. Bootstrap up to one year with `POST /api/context/official/backfill?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`, then call `POST /api/context/official/rebuild`. The operation is read-only and never uses broker credentials.
- Known split, bonus, cash-dividend and rights actions are reconciled point-in-time and applied before candle persistence. Merger/demerger reconstruction is allowed only for an explicit official factor with confirmed same-symbol continuity; ratio-only or cross-symbol schemes remain blocked. Conflicts or unsupported terms produce `REJECT_DATA_INTEGRITY` before harmonic analysis.
- BSE buyback/open-offer indexes are discovery metadata. Linked official XBRL terms are archived and revisioned separately and remain contextual evidence that cannot independently unlock `READY`.
- The default research account size is INR 1,00,000. Quantity is stop-risk constrained; confidence cannot override hard limits.
- Position sizing reads persisted settings and safety state, then applies total-risk, sector-risk, correlation, liquidity, margin and lot caps. Daily loss, cooldown and panic states override confidence and return zero quantity.

See `docs/BUILD_STATUS.md` and `docs/VALIDATION.md` for verified current behavior and remaining work.
See `docs/DEPENDENCIES.md` for the verified license inventory and disabled incompatible adapters.
See `TREND_FORGE_SOURCE_REGISTRY.md`, segment `S012`, for the immutable 211-link audit and performed fetch results.


<!-- CONSOLIDATED_SOURCE_END label=README sha256=ED58DFF72D2C1663BF50BCF365F304E3365E654ACC3026A073D19C013DD92874 -->



<!-- CONSOLIDATED_SOURCE_BEGIN
label: REVIEW
original_path: REVIEW.md
line_count: 169
byte_count: 7064
sha256: 2C65E3A5CC8D561A0922FD2C8859D88D153203543D2B50EC5926E9E87BD542DE
copy_mode: VERBATIM_BYTES
-->
<a id="embedded-source-review"></a>

## EMBEDDED SOURCE: REVIEW.md

# Review - Source Inventory Audit And Clean Data Slice

## Self-Critique

- The audit accounts for all 211 links but intentionally fetches only selected
  batches. It is not evidence that every link is connected or useful.
- Generic payload profiling improves discovery, but source-specific parsers are
  still required before fields have financial meaning.
- The active source catalog now has 32 descriptors. Remaining documentation
  that quotes older 27/30-source snapshots is historical, not current truth.

## Requirement Coverage

- Complete inventory accounting, raw archive, per-link outcomes and API access:
  complete.
- Clean CSV/JSON profiling and strict FRED normalization: complete.
- Metadata/HTML conversion into trading evidence: deliberately blocked.
- AMFI, NSE SLB and MCX official artifact contracts: still pending.
- READY authority: unchanged; audit rows always have `can_unlock_ready=0`.

## Three Failure Risks

1. Official providers can change download endpoints or JSON envelopes; schema
   mismatch must continue to block parsing.
2. Browser-rendered sites can expose incomplete tables or anti-bot pages; these
   must remain metadata even when they look visually valid.
3. Running broad network audits too aggressively can trigger provider rate
   limits; batches, throttle, timeout and maximum-byte controls are mandatory.

## Two Optimizations

1. Prioritize unresolved official gate sources by scanner value instead of
   fetching all remaining reference/commercial links uniformly.
2. Cache immutable content hashes and skip normalization only when source key,
   parser version and schema hash are unchanged.

## Security Review

The primary security risk is server-side request forgery if arbitrary URLs are
later accepted from API callers. The current API accepts inventory IDs only;
keep that allowlisted boundary, localhost binding and bounded response sizes.
Do not add a free-form URL fetch endpoint without host allowlists, private-IP
blocking, redirect validation and authentication.

## Verification

```text
Backend tests       201 passed
Frontend acceptance 95/95 passed
Ruff                passed
Mypy                passed
Compileall           passed
Runtime health       ok on 127.0.0.1:8001
```

## 2026-07-13 Source Activation Review

The new MCX embedded-data path and NSE SLB archive path improve official EOD
coverage without relaxing `READY`. Remaining risks are source HTML schema
drift, MCX response size, and interpreting SLB outstanding quantity as exact
short interest. Parser fixtures and scope labels cover these boundaries.

Required follow-up: add an MCX-specific response-size policy and exchange
calendar, then build a separate strike-aware MCX options table before any
IV/Greeks adapter is connected.

Self-critique: this turn converts three high-value sources, not all remaining
143 contracts. The row-level matrix makes that boundary explicit. The next
highest-value work is AMFI AMC workbook normalization, MCX exchange-calendar
freshness and verified option-chain/basis inputs; none should be represented as
complete before live fixture and schema tests pass.

## 2026-07-13 Nine-Source Fetcher Review

### Self-Critique And Coverage

- The submitted endpoints are connected and live verified, but PIT and option
  chain currently contain no rows and therefore remain context unavailable.
- Pledge data is preserved exactly but cannot be scored by symbol until an
  ISIN/company identity join is versioned and verified.
- OI spurts add timely activity evidence but do not solve the missing MWPL
  denominator, rollover, live basis, IV or Greeks requirements.
- G03 ASM/GSM safety, raw lineage, normalized storage, freshness and frontend
  visibility are complete for this milestone.

### Three Failure Risks

1. NSE or NSDL can change JSON/HTML schema; strict mismatch must remain WAIT.
2. A valid empty surveillance list could be confused with a broken response;
   only parser-marked, source-dated `validEmpty` is allowed to pass.
3. Company-name-only pledge rows can join to the wrong listed entity unless
   identity mapping is point-in-time and ambiguity-aware.

### Two Optimizations

1. Cache per-symbol surveillance and OI-spurt membership for an all-NSE run.
2. Materialize typed NSDL daily totals while preserving the immutable rows.

### Security Review

The new endpoints are fixed allowlisted URLs. The main security risk would be
generalizing them into a caller-controlled fetch URL, which could introduce
SSRF. Keep fixed contracts, redirect validation, response-size limits and raw
archive hashing.

### Verification

```text
Backend tests       239 passed
Frontend acceptance 95/95 passed
Ruff                passed
Mypy                passed with external untyped imports ignored
Compileall           passed
```

## 2026-07-13 Institutional Engine Review

Potential failures: public market endpoints can change schema or reject cookie
sessions; model packages can be installed without a valid trained artifact;
factor inputs can be correlated and overstate confidence. Mitigations now in
code are immutable raw archives, client-readiness rejection, source-owner links,
anomaly separation and fail-closed missing factors.

Optimizations still required: batch normalization should reuse canonical source
artifacts instead of refetching; all-universe factor calculation should use
vectorized cached candle frames. Security boundary: the server is localhost by
default and has no authentication, so it must not be exposed to a network until
authentication, CSRF policy and deployment rate limits are added.

## 2026-07-13 Gold Context Source Review

### Self-Critique And Coverage

- WGC and SGE are structured delayed context, not intraday execution evidence.
- SGE premium is intentionally not calculated until synchronized benchmark,
  FX, units and tax-policy inputs exist.
- LME warehouse details and MCX delivery notices remain unresolved because a
  stable legal automated artifact was not obtained.

### Three Failure Risks

1. Undocumented WGC JSON schema drift could change nested series semantics.
2. SGE may publish a valid holiday page with no rows; date/schema guards must
   continue distinguishing that from a transport success.
3. Correlated WGC OI, ETF holdings and ETF flows could be double-counted by a
   future score unless evidence-family caps are enforced.

### Two Optimizations

1. Materialize only the latest plus configured rolling history for dashboard
   queries while retaining the immutable raw archive.
2. Add an evidence-family correlation key so multiple WGC datasets enrich an
   explanation without multiplying confidence.

### Security Review

All runtime URLs are fixed and allowlisted. The primary security risk is future
support for caller-supplied source URLs, which could create SSRF. Keep redirect
validation, response-size limits and fixed source contracts.

### Verification

```text
Backend tests       248 passed
Frontend acceptance 95/95 passed
Ruff lint/format    passed
Mypy                passed
Compileall           passed
```


<!-- CONSOLIDATED_SOURCE_END label=REVIEW sha256=2C65E3A5CC8D561A0922FD2C8859D88D153203543D2B50EC5926E9E87BD542DE -->



<!-- CONSOLIDATED_SOURCE_BEGIN
label: IMPLEMENTATION_PLAN
original_path: TREND_FORGE_IMPLEMENTATION_PLAN.md
line_count: 4446
byte_count: 173030
sha256: 492855467DD054282F14F513EF7C0D26C156C224AEF28C59C7D3975286AC1918
copy_mode: VERBATIM_BYTES
-->
<a id="embedded-source-implementation-plan"></a>

## EMBEDDED SOURCE: TREND_FORGE_IMPLEMENTATION_PLAN.md

# TrendForge Implementation And Verification Plan

Date: 2026-07-11
Status: GUARDED_RESEARCH_MILESTONES_IMPLEMENTED_LIVE_MILESTONES_PENDING
Authority: Companion to `present.md` and `TREND_FORGE_ARCHITECTURE.md`

## 1. Delivery Rule

The user authorized implementation of the guarded local framework. Further milestones still require tests, runtime verification, self-review and updates to the four canonical documents.

A milestone is not complete because files/endpoints exist. Completion requires correct behavior, failure handling, persisted evidence and passing acceptance criteria.

OpenAlgo live brokerage integration is deferred until the user supplies the actual contract and configuration. No broker execution path is currently enabled.

## 2. Definition Of Done

Every milestone includes:

- requirements mapped to files and tests;
- typed domain/API contracts;
- deterministic error states;
- source/evidence lineage;
- unit, property and failure tests;
- API/integration tests;
- migration and rollback notes;
- frontend/browser checks when visible;
- structured logs for new boundaries;
- updated four-document status;
- no fail-closed regression.

## 3. Milestone 0 - Safety Foundation

Goal: ensure mock, stale, incomplete or wrongly scoped evidence cannot reach the bot as executable.

Likely files:

```text
backend/trendforge_api/main.py
backend/trendforge_api/engine.py
backend/trendforge_api/gate_readiness.py
backend/trendforge_api/models.py
backend/trendforge_api/source_contracts.py
backend/tests/
frontend/index.html
frontend/app.js
frontend/styles.css
frontend/tests/
```

Work:

1. Add `executable`, reason codes, blockers, generated/data-cutoff/expiry timestamps.
2. Remove mock rows from normal radar.
3. Move demo data behind explicit demo mode and persistent banner.
4. API failure yields OFFLINE/NO DATA and zero executable candidates.
5. Correct G12, G13 and MCX gate contracts.
6. Enforce symbol/market/source scope.
7. Require parse output to match active snapshot.
8. Make source-specific valid-empty behavior consistent.
9. Restrict CORS to localhost.
10. Test that no mock/unofficial/stale/metadata-only input can produce executable READY.

Acceptance:

```text
MWPL alone cannot pass G13
large deal alone cannot pass full G12
CFTC alone cannot pass MCX
new snapshot plus old parse blocks
API offline shows no candidate
demo candidates executable=false
unknown source/scope blocks
```

Complexity: Medium.
Risk: current frontend assumes five mock rows.

## 4. Milestone 1 - Database, Lineage And Configuration

Goal: durable point-in-time truth.

Work:

- migration/version table;
- `foreign_keys=ON`, WAL and busy timeout;
- normalized instruments, artifacts, parser runs, evidence, scans and links;
- immutable raw artifacts;
- exact snapshot/parser/gate IDs per candidate;
- INR 1,00,000 account defaults;
- transactional scan/candidate/gate persistence;
- backup/restore command;
- stop reseeding editable registry rows on reads;
- retention references preventing deletion of used artifacts.

Tests:

- interrupted/duplicate migration;
- orphan FK;
- DB lock and bounded retry;
- partial scan failure;
- backup restored elsewhere;
- disk-space guard;
- concurrent read/job behavior.

Acceptance: an old result is reproducible after later source and parser versions arrive.

Complexity: High.

## 5. Milestone 2 - Correct Existing Parsers

Goal: make current parser families correct against realistic official schemas.

Work:

1. Explicit field aliases per source/schema version, no loose substring guessing.
2. Reject empty normalized keys.
3. Fix participant futures double counting.
4. Store index/stock futures and call/put long/short separately.
5. Remove unsupported directional participant-OI claims.
6. Correct large-deal client/side mapping.
7. Split bulk and block ingestion.
8. Correct CFTC producer/merchant, swap, managed-money and nonreportable fields.
9. Use historical percentiles for commercial COT interpretation.
10. Store full MCX OHLC/settlement/contract identity.
11. Add bounded XLS/XLSX reader for AMFI.
12. Version parsers and fixtures.

Real-file fixtures:

```text
NSE MWPL and ban
NSE participant OI
NSE bulk and block
AMFI workbook variants
CFTC current/historical disaggregated
MCX bhavcopy variants
```

Invariants:

- no double count;
- side/client/symbol cannot cross-map;
- percentages bounded;
- future dates rejected;
- malformed values are unknown, not zero truth;
- ZIP/XLSX size limits;
- order-independent columns;
- schema change quarantines.

Acceptance: manually verified fixture rows match normalized rows.

Complexity: High.

## 6. Milestone 3 - Resolver, Freshness And Archive

Goal: distinguish a new report from an old page, anti-bot page or wrong file.

Work:

- one resolver per artifact family;
- status/MIME/magic-byte/size validation;
- bounded backoff/jitter and domain rate limits;
- attempted URL/error audit;
- market-calendar freshness;
- source data date and publication time;
- `fetch=false` check record without replacing valid artifact;
- content hash retrieval history;
- decompression limits;
- parser cache by hash/version;
- retention and checksum verification.

Acceptance tests:

```text
HTML returned from CSV URL -> quarantine
dynamic token with same report -> unchanged
new report same size -> changed
weekend/holiday -> correct freshness
fetch=false -> last valid remains
403/429/500 -> stale visible and gate blocked
```

Complexity: High.

## 7. Milestone 4 - Candles And Exchange Calendar

Goal: one authoritative reproducible candle sequence per scan.

Work:

- source-specific candle identity;
- revision-aware upsert;
- duplicate/gap/session/timezone validation;
- corporate-action adjustment versions;
- exact NSE/MCX calendars;
- fix 4H expected input-bar calculation;
- partial afternoon bar state;
- atomic Parquet merge/dedupe/partition;
- safe path validation;
- DuckDB analytical access;
- retention jobs.

Tests:

- mixed sources never enter one scan;
- corrected candle replaces projection and keeps revision;
- 48 x 5m bars = complete 4H;
- holiday/special session;
- UTC/IST boundary;
- split-adjusted history;
- incremental Parquet retains old rows;
- path traversal rejected;
- corrupt Parquet quarantined.

Acceptance: a candle revision hash deterministically reproduces downstream results.

Complexity: High.

## 8. Milestone 5 - Harmonic Correctness

Goal: no-lookahead research-grade harmonic detector.

Work:

- correct XAD/all ratios;
- enumerate pivot windows;
- pivot occurrence and confirmation timestamps;
- converging-projection PRZ;
- pattern-specific invalidation/targets;
- multi-sensitivity consensus;
- MTF alignment/conflict;
- complete lifecycle;
- source/corporate-action gates;
- real chart overlay.

Bullish and bearish fixtures:

```text
AB=CD/ABCD, Gartley, Bat, Butterfly, Crab,
Deep Crab, Cypher, Shark, Five-0
```

Adversarial cases:

- near miss;
- flat leg;
- duplicate pivots;
- split/gap;
- missing volume;
- no future confirmation;
- repaint attempt;
- overlaps;
- gap through PRZ;
- illiquidity.

Acceptance: no historical action before pivot/pattern confirmation.

Complexity: High.

## 9. Milestone 6 - Official Stock Sources

Goal: complete EOD smart-money and safety evidence.

Deliver separately authorized parser slices:

```text
NSE EOD/security master
NSE F&O bhavcopy
NSE SLB
NSE corporate actions and daily buyback
NSE ASM/GSM/suspension
BSE deals, buyback/open offer and filings
SEBI PIT/SAST/pledge/FPI
AMFI adjusted month-over-month deltas
MSEI FII/DII contribution
RBI FPI constraints
MCA background later
```

Add insider quality, deal anchors, AVWAP, supply overhang/absorption and corporate-action-adjusted holdings.

Acceptance: G12 explains specific symbol/cutoff evidence, staleness and not-applicable states.

Complexity: Very high.

## 10. Milestone 7 - Futures, Options, IV And Greeks

Goal: stock-level derivative reliability.

Work:

- contract/expiry master;
- spot/near/next basis;
- point-in-time OI quadrant;
- MWPL/ban;
- rollover/expiry mode;
- future OpenAlgo option-chain adapter;
- IV, rank/percentile, term structure and skew;
- instrument-appropriate Black/BSM/Black-76 Greeks;
- PCR/strike walls as context;
- SLB proxy;
- participant OI remains regime-only.

Tests:

- MWPL 80/90/95;
- ban;
- rollover versus closure;
- all OI quadrants;
- basis conflict;
- expired/zero-time option;
- price below intrinsic;
- ITM/OTM numerical stability;
- missing rate/dividend;
- IV solver failure;
- call/put signs;
- corporate-action strike adjustment.

Acceptance: G13 cannot pass from MWPL alone and reports all derivative components separately.

Complexity: Very high; live completion depends on future OpenAlgo contract.

## 11. Milestone 8 - MCX Engine

Goal: active MCX scanning with commodity-specific context.

Work:

- MCX contract/lot/tick/expiry/delivery master;
- complete official OHLCV/OI and near/far basis;
- USD/INR;
- CFTC history/percentiles;
- Gold/Silver global and physical context;
- Crude/NG EIA/API/OPEC/event engine;
- LME/SHFE/China base-metal engine;
- USDA/IMD/agri engine;
- session-aware ORB/VWAP and event lockouts;
- commodity risk/correlation caps.

Acceptance: no MCX READY from local MCX price alone or CFTC alone; Gold always includes currency; delivery risk explicit.

Build commodity families individually, beginning with Gold Mini after contracts are proven.

Complexity: Very high.

## 12. Milestone 9 - Real Universe And Scheduler

Goal: replace mock slicing with real all-NSE and active-MCX scans.

Work:

- instrument catalog refresh;
- liquidity/tradability prefilter;
- EOD universe queue;
- intraday incremental liquid queue;
- persistent market-calendar jobs;
- rate limits and job locks;
- abandoned-run recovery;
- progress/skipped reasons;
- evidence bundle per candidate;
- save WAIT/REJECT/CONFIRMED.

Tests:

- EOD/watchlist performance;
- bounded memory;
- manual/scheduled dedupe;
- restart recovery;
- slow source isolation;
- holiday behavior;
- zero/unavailable universe.

Acceptance: candidate count comes from real processed instruments with exact cutoff/evidence IDs.

Complexity: Very high.

## 13. Milestone 10 - Risk, Emotional Safety And Trade Intent

Goal: calculate safe quantity and expose non-live bot interface.

Work:

- persisted settings;
- stop/slippage/fee sizing;
- lot/margin/liquidity caps;
- portfolio correlation;
- FOMO/ATR;
- cooldown/consecutive-loss/daily lock;
- immutable expiring trade intent;
- idempotency/local token;
- fake OpenAlgo adapter;
- bot acknowledgement events.

Tests:

- confidence cannot exceed risk cap;
- valid lot rounding;
- missing stop = zero;
- hard loss cannot bypass;
- duplicate/expired signal rejected;
- price beyond slippage expires;
- correlation reduces quantity;
- WAIT/REJECT executable=false;
- no secret in logs/database.

Acceptance: fake bot receives only valid READY intents and rejects intentionally corrupt payloads.

Complexity: High. Real OpenAlgo remains disabled until user supplies details.

## 14. Milestone 11 - Outcomes, ML And Backtest

Goal: learn from failures without weakening safety.

Work:

- point-in-time feature vectors;
- trigger/MAE/MFE/target/stop labels;
- outcome workers;
- walk-forward engine;
- costs/fills/slippage;
- confidence calibration;
- failure clusters;
- champion/challenger registry;
- model cards/dataset manifests;
- paper/shadow evaluation.

Leakage tests:

- no future candles;
- publication delays enforced;
- AMFI unavailable before release;
- CFTC unavailable before Friday publication;
- pivots unavailable before confirmation;
- point-in-time universe;
- corporate actions only when known.

Acceptance: thresholds in `present.md` pass; ML cannot modify hard gates or execute.

Complexity: Very high.

## 15. Milestone 12 - Frontend Completion

Goal: trustworthy single-screen operation.

Work:

- real candidates only;
- sanitized DOM;
- real candles/patterns/anchors;
- data cutoff/source age;
- pass/block/not-applicable gates;
- quantity explanation;
- stale/offline/demo banners;
- saved state filters;
- parser/source/scanner drilldown;
- settings and safety controls;
- keyboard/responsive support.

Browser tests:

```text
1440 and 1920 desktop
390 mobile
no overlap/overflow
offline/stale/no-candidate
hundreds of candidates
lock states
parser errors
XSS rendered as text
real chart nonblank
```

Acceptance: UI never implies executable READY against backend state.

Complexity: Medium/high.

## 16. Milestone 13 - Production Hardening

Goal: safely support a real local trading bot.

Work:

- isolated locked environment;
- dependency audit;
- structured logs/rotation;
- health/readiness/liveness;
- backup/restore runbook;
- retention;
- local token/CORS;
- rate/payload limits;
- Windows service;
- monitoring/kill switch;
- release/rollback.

Acceptance:

- clean-machine reproducibility;
- restore test;
- restart-safe jobs;
- disk/DB/source failures fail closed;
- no unresolved high-severity dependency issue;
- 30-day shadow run without false executable state.

Complexity: High.

## 17. Cross-Cutting Test Matrix

| Area | Unit | Property | Integration | E2E | Replay |
| --- | --- | --- | --- | --- | --- |
| Parsers | Required | Required | Required | Optional | Required |
| Candles | Required | Required | Required | Optional | Required |
| Harmonics | Required | Required | Required | Chart | Required |
| Gates | Required | Required | Required | Candidate UI | Required |
| Risk | Required | Required | Required | Bot fake | Required |
| Scheduler | Required | Useful | Required | Status UI | Recovery |
| ML/backtest | Required | Required | Required | Reports | Required |
| Frontend | Useful | Optional | API | Required | Optional |

## 18. Mandatory Failure Cases

```text
no snapshot; skipped fetch; 403/404/429/500; timeout/truncation
wrong MIME/magic bytes; oversized archive; metadata-only page
renamed/missing columns; valid/invalid empty; future/stale date
latest snapshot with old parse; source-scope mismatch
holiday/special session; duplicate/revised/mixed candles
unadjusted corporate action; lookahead pivot; ratio near miss
MWPL/ban/expiry distortion; IV numerical failure
source loss during scan; DB lock; disk full; concurrent jobs
restart during job; daily/emotional lock; duplicate/expired signal
frontend offline/stale/XSS; model/data drift
```

## 19. Review Template

Each milestone records:

```text
scope and files
tests and exact results
runtime proof
assumptions and remaining gaps
three failure risks
two optimizations
one security concern
rollback
authorization needed next
```

## 20. Completed Build Slice - 2026-07-10

| Slice | Status | Acceptance evidence |
| --- | --- | --- |
| Fail-closed radar and demo isolation | Complete | zero READY rows; demo rows are WAIT only |
| SQLite/Parquet candle persistence | Complete | stored series scanned and features saved |
| Harmonic detector and G00-G14 | Complete for research | real stored scans produce guarded REJECT/WAIT only |
| Raw archive/parser/freshness framework | Complete | latest-snapshot, schema, date and stale blocks tested |
| Official parser fixtures | Complete | CFTC, NSE, BSE, AMFI, SEBI and MCX parsers covered |
| Row-level domain storage and drilldown | Complete | parser tables and frontend drilldown present |
| Controlled scanner scheduler | Complete for single process | persisted status, overlap lock, off by default |
| Risk settings and position sizing | Complete | INR 1 lakh defaults and deterministic risk tiers tested |
| Options math | Complete as calculation service | price, Greeks and bounded IV tested; live quote input pending |
| Feature engineering and harmonic validation | Complete baseline | point-in-time cutoff and no-future-candle validation tested |
| CFTC historical analytics | Complete baseline | official disaggregated archives, no-lookahead rolling features, stale/context-only enforcement |
| Observability/local security | Complete baseline | request IDs, structured logs, local CORS, bounded inputs |
| Clean environment reproducibility | Complete | requirements-dev, clean pip check, 50 tests |
| Browser acceptance | Complete baseline | 70 checks, no console errors, desktop/mobile no overflow |

## 21. Remaining Milestone A - Verified Live Data

Purpose: replace research-only and fixture-only inputs with verified current evidence without weakening the gates.

Required work:

1. verify official direct-download/API contracts for every required NSE/BSE/AMFI/SEBI/MCX/CFTC source;
2. obtain and validate exchange universe/instrument masters, symbol/ISIN/expiry mapping and corporate-action adjustment history;
3. connect a legal live intraday source for NSE and MCX, with sequence, exchange timestamp, revision and outage rules;
4. populate synchronized spot/futures/options quotes for OI, basis, rollover, IV and Greeks;
5. populate mandatory MCX context including USD/INR and commodity-specific global sources;
6. run EOD shadow scans, then intraday watchlist scans, before all-universe intraday scans;
7. keep the last valid row visible as STALE but block executable use.

Acceptance:

```text
official raw bytes archived and replayable
live schema contracts pass real-file fixtures and revisions
source dates and publication lag are correct
all symbol/market scope tests pass
no unofficial-only READY
Nifty/MCX shadow scan meets duration and completeness targets
30 consecutive shadow days without a false executable state
```

## 22. Remaining Milestone B - OpenAlgo Integration

Purpose: connect only verified, expiring TrendForge intents to the user's existing bot.

Build after the user supplies OpenAlgo endpoint/auth/instrument conventions:

1. credential-blind frontend and environment-only secret storage;
2. versioned OpenAlgo adapter with timeout, retry policy and circuit breaker;
3. signed/idempotent trade intent and duplicate suppression;
4. broker-side quote, market status, margin, position, quantity, lot and price-band revalidation;
5. paper mode, shadow mode and explicit live enable switch;
6. order acknowledgement, partial fill, rejection and cancellation reconciliation;
7. kill switch, daily hard lock and restart-safe state;
8. immutable intent/order/outcome audit records for ML labels.

Live permission is not granted by passing tests alone. It requires user-supplied credentials, paper evidence and an explicit enable action.

## 23. Verification Record

```text
2026-07-10 backend: 55 passed
2026-07-10 clean isolated backend: pip check clean, 55 passed
2026-07-10 frontend: 74/74 acceptance checks
2026-07-10 compile/syntax: Python and JavaScript passed
2026-07-10 database: integrity ok, WAL, app FK=1, busy timeout=5000
2026-07-10 runtime: scanner COMPLETE, 2 stored series, source gates blocked, 0 READY
2026-07-10 browser: no console errors, no desktop/mobile horizontal overflow
2026-07-10 CFTC: 6 official annual archives attempted; optimized resume completed 2024-2026 after a timed-out first pass
2026-07-10 CFTC store: 287 weekly dates, 3,170 normalized positions and feature rows, DB integrity ok
```

## 24. Next Action

Do not relax a gate to create candidates. The next build starts with verified live source contracts and instrument mapping. Real OpenAlgo integration remains the final phase and begins only after the user provides its configuration.

## 25. Replacement Data-To-Decision Plan

### 25.1 Why The Earlier Plan Was Not Sufficient

The earlier milestones correctly described components but did not specify how downloaded data becomes a defensible stock selection. It left five dangerous ambiguities:

1. it treated source integration as a parser task instead of a point-in-time evidence problem;
2. it did not assign each dataset a precise decision job;
3. it did not prevent several websites repeating the same underlying event from inflating confidence;
4. it did not define enough cleaning, reconciliation and revision behavior;
5. it did not show exactly how a stock moves from the full NSE universe to `WAIT`, `READY` or `REJECT`.

This section replaces that shallow interpretation. The 209 saved URLs are an inventory, not 209 votes. Only independent, scoped, fresh and reproducible evidence may influence selection.

### 25.2 Business Outcome

For every scan cutoff, the system must answer:

```text
Why is this instrument moving?
Who or what is likely sponsoring the move?
Is price/volume/derivatives behavior accepting or rejecting that cause?
Is the evidence known at this cutoff, independent and fresh?
Where is the invalidation level?
Is expected reward sufficient after slippage, fees and event risk?
What quantity is safe for the INR 1,00,000 account?
What exact missing or conflicting fact prevents action?
```

The output is evidence-ranked research guidance for the user's bot interface. It is not executable until the later OpenAlgo milestone revalidates market state, quote, margin, quantity and all locks.

## 26. Five Jobs For All Data

Every source and normalized field must be assigned one or more explicit jobs. Unassigned data is stored for research but cannot affect a score or state.

| Job | Question answered | Examples | Decision effect |
| --- | --- | --- | --- |
| Eligibility veto | Is this safe and tradeable? | listing status, ASM/GSM, suspension, price band, liquidity, F&O ban, MWPL, expiry/delivery | Hard block, warning or not-applicable |
| Causal trigger | Why could repricing begin now? | results, order, regulation, buyback, open offer, inventory surprise, OPEC/EIA event | Starts a candidate thesis with event timestamp |
| Sponsor proof | Is informed or persistent capital participating? | graded insider buy, bulk/block buyer, AMFI delta, buyback execution, delivery/absorption | Raises or weakens sponsorship block |
| Flow confirmation | Is fresh money entering in the expected direction? | RVOL-TOD, trade size, delivery, OI quadrant, basis, IV/skew, SLB | Confirms, conflicts or remains unknown |
| Execution/risk | Can this be entered now at acceptable cost and invalidation? | spread, depth, ATR, VWAP/AVWAP, gap, stop, target, correlation, event clock | Timing state and quantity cap |

The same observation cannot count in two independent evidence blocks. For example, one bulk-deal disclosure may create a cause, sponsor identity and price anchor, but its maximum independent contribution remains one event-family vote.

## 27. Data Authority And Use Hierarchy

### 27.1 Source Roles

```text
OFFICIAL_OR_LICENSED_GATE
  May support a gate only after structured, fresh, scope-correct parsing.

OFFICIAL_DELAYED_CONTEXT
  May influence regime or swing sponsorship with explicit lag decay.

CALCULATED_DERIVATIVE
  Locally calculated from traceable inputs; formula/version required.

SECONDARY_DISCOVERY
  May create a fetch lead, never proof.

REFERENCE_ONLY
  May teach schema, UX or validation; never enters candidate evidence.

UNOFFICIAL_RESEARCH
  May support development, comparison and shadow scans; never executable READY.
```

### 27.2 Independence Families

Evidence is grouped by underlying origin, not by website count:

| Family | Examples that belong to one family |
| --- | --- |
| Exchange filing | NSE page, BSE page, SEBI mirror and aggregator copy of the same disclosure |
| Cash tape | OHLCV, VWAP, RVOL, trade count and delivery derived from the same exchange session |
| Derivatives tape | futures price/OI/basis/rollover from the same contract feed |
| Options surface | option OI, IV, skew, PCR and Greeks from the same synchronized chain |
| Ownership | AMFI scheme files, shareholding pattern and depository aggregates, separated by publication period |
| Borrow pressure | SLB transactions/positions; never duplicated as exact short interest |
| Global commodity | CFTC, EIA, OPEC, LME, SHFE, SGE and physical reports, each scoped to its own publication |

Correlated features inside one family improve interpretation but do not multiply independent confidence.

## 28. Source-To-Decision Utilization Matrix

| Normalized dataset | Required fields | Cleaning/reconciliation | Derived evidence | Stock-selection use |
| --- | --- | --- | --- | --- |
| NSE/BSE security master | symbol, ISIN, series, listing status, face value, lot, effective dates | ISIN-first identity, symbol history, duplicate/exclusive listing rules | active universe, series eligibility | Remove suspended/inactive/wrong-series instruments |
| NSE/BSE EOD tape | OHLC, VWAP, volume, value, trades, delivery, data date | OHLC invariants, duplicate key, unit and revision checks | ATR, turnover, trade size, delivery z-score, gaps, RS | Liquidity prefilter, structure and flow |
| Intraday candles | exchange timestamp, OHLCV, sequence/source | timezone/session/gap/duplicate/revision checks | RVOL-TOD, ORB, VWAP, AVWAP, wick/absorption, MTF | Intraday timing and setup quality |
| Corporate actions | action, announcement/ex/record dates, ratio, amount | effective-date and adjustment-factor validation | adjustment chain, event-risk clock | Block unadjusted history; normalize price/volume/holdings |
| Announcements/results | category, event time, document, values | dedupe NSE/BSE copies, classify event, preserve document hash | surprise/catalyst type, age, materiality | Cause block; never bullish merely because news exists |
| PIT/insider | person, relationship, mode, side, quantity, price, holdings | open-market vs ESOP/transfer/pledge classification | insider quality, notional, ownership change, anchor | Sponsor proof with quality grading |
| Bulk/block deals | client, side, quantity, price, deal type | buyer/seller mapping, same-event dedupe, close comparison | premium/discount, deal anchor, absorption, supply overhang | Sponsor and acceptance evidence |
| Buyback/open offer | type, offer price, size, period, daily execution | announced vs approved vs active vs completed | price magnet, company demand, remaining capacity | Cause/sponsor context, not standalone READY |
| AMFI holdings | AMC, scheme, ISIN, quantity, value, AUM %, period | corporate-action-adjust prior month, map ISIN, handle mergers | new entry, add/reduce/exit, breadth across AMCs | Delayed swing sponsorship only |
| Shareholding/pledge | holder class, holding %, pledge %, period | compare same basis/period, distinguish release/invocation | ownership delta, pledge risk | Sponsor/risk; no intraday timing claim |
| FII/DII cash | date, gross/net values | cross-exchange date reconciliation | market sponsorship regime | Market context only, not stock attribution |
| Participant OI | participant, instrument, long/short, date | prevent futures/options double count | FII/DII/Pro/Client index regime | Regime only, never stock-level proof |
| MWPL/ban | symbol, MWPL %, ban status, date | valid-empty rules, F&O membership check | OI reliability tier | Must pass before stock OI interpretation |
| F&O tape | symbol, expiry, futures price, OI, volume, turnover | contract identity, expiry and spot synchronization | OI quadrant, basis, carry, rollover | Directional flow/conflict evidence |
| Options chain | expiry, strike, call/put, bid/ask, LTP, OI, IV, volume | crossed/stale quote checks, intrinsic bounds, synchronized spot/rate | IV rank, skew, term structure, walls, Greeks | Confirmation and event-risk; never pattern-only trade |
| SLB | symbol, series, lend/borrow, fee/yield, open position | settlement-series mapping and valid-empty handling | borrow pressure, fee percentile, squeeze context | Proxy warning/confirmation, not exact short interest |
| ASM/GSM/bands | symbol, stage, effective date, band | latest-effective file and stage transition | operator/surveillance risk | Hard reject or severe quantity restriction |
| Sector/index tape | constituent weights, returns, breadth, volume | point-in-time constituents and rebalance dates | sector RS, breadth, RRG phase, leader/laggard | Sector gate and relative-strength ranking |
| Calendar/events | release/ex/expiry/holiday timestamps | timezone and revision-aware schedule | minutes to event, event lock, expiry mode | Prevent binary-event and closed-session entries |
| MCX/CFTC/global | contract, OI, position categories, inventory, FX, report/release dates | contract mapping, units, lag and revision checks | commodity regime, parity, basis and crowding | MCX branch only; cannot prove NSE stock sponsorship |

## 29. Acquisition And Download Design

### 29.1 Resolver Contract

Each artifact family gets a dedicated resolver. A generic HTML scraper is not acceptable for gate data.

```text
source_key
artifact_family
canonical_landing_url
resolved_download_url
request_method and permitted headers
expected MIME and magic bytes
expected filename/date pattern
maximum compressed/uncompressed size
publication calendar and grace
valid-empty policy
parser name/version and schema version
authority role and allowed decision jobs
```

Resolver output states:

```text
NOT_DUE
FETCHED_NEW
UNCHANGED_HASH
REVISED_SAME_DATE
ACCESS_RESTRICTED
RATE_LIMITED
ANTI_BOT_OR_HTML
WRONG_ARTIFACT
TRUNCATED
BROKEN
```

Only `FETCHED_NEW`, `UNCHANGED_HASH` and a validated `REVISED_SAME_DATE` may proceed. An old valid artifact remains visible after failure but is marked stale according to its publication clock.

### 29.2 Fetch Manifest

Every attempt is recorded, including failures:

```text
fetch_id, source_key, artifact_family, attempted_at_utc
canonical_url, resolved_url, status_code, redirect_chain
request_headers_hash, response_headers, content_type
content_length, compressed_size, uncompressed_size
sha256, etag, last_modified
expected_data_date, detected_data_date
attempt_number, duration_ms, state, error_code
resolver_version, host_rate_limit_bucket
```

### 29.3 Immutable Raw Archive

```text
data/raw/<source_key>/<artifact_family>/
  data_date=YYYY-MM-DD/
    fetched_at=YYYYMMDDTHHMMSSZ_<sha256-prefix>.<original-extension>
    manifest_<fetch_id>.json
```

Rules:

1. never overwrite bytes;
2. content-address identical files;
3. retain every revision that influenced a scan;
4. verify checksums periodically;
5. quarantine decompression bombs, HTML masquerading as CSV and password-protected files;
6. keep source terms/licensing metadata beside the resolver contract;
7. block fetch before disk exhaustion, never delete referenced artifacts automatically.

### 29.4 Scheduler By Information Value

| Window | Required jobs | Why |
| --- | --- | --- |
| 05:30-08:30 IST | global close, CFTC when due, macro/event calendars, stale audit | Build regime without racing NSE pages |
| 08:30-09:05 | instrument/ban/MWPL/ASM-GSM/calendar refresh, prior EOD validation | Establish hard safety state before candidates |
| 09:15-11:30 | licensed/OpenAlgo incremental candles and synchronized derivatives for liquid queue | Primary intraday discovery window |
| 11:30-14:15 | reduced cadence, monitor active candidates and source health | Avoid wasteful all-universe full recomputation |
| 14:15-15:30 | closing strength, delivery proxy where available, swing trigger updates | Capture close-quality evidence |
| 16:00-20:00 | EOD bhavcopy/delivery/F&O/deals/filings/corporate actions | Build official daily truth |
| 20:00-23:00 | clean, reconcile, features, outcomes, EOD scan, report | Produce next-session swing/watch plan |
| Weekly/monthly | CFTC, AMFI, shareholding, imports, reserves, LME/SHFE/USDA/IMD as due | Update delayed regime/sponsorship without pretending live flow |

All times are configuration, not hardcoded truth. Publication detection uses actual artifact dates and market calendars.

## 30. Cleaning And Reconciliation Pipeline

Cleaning is a deterministic series of stages. Each stage writes its own status and rejects rather than silently repairing ambiguous records.

### 30.1 Stage C0 - Byte Validation

Validate status, MIME, magic bytes, archive members, size, checksum and encoding. Reject login pages, bot challenges and partial downloads.

### 30.2 Stage C1 - Schema Detection

Match an explicit known schema signature. Column aliases are source/version-specific. Unknown schema becomes `SCHEMA_MISMATCH`; fuzzy substring matching cannot unlock a gate.

### 30.3 Stage C2 - Type And Unit Normalization

Normalize dates, timestamps, decimal separators, percentages, prices, quantities, contracts, currency and units. Preserve original text and parsed value. Unknown is `NULL` plus reason, never zero.

### 30.4 Stage C3 - Identity Resolution

Use ISIN for cash equities; exchange instrument/token plus effective dates for live data; symbol-expiry-strike-type for derivatives; exchange commodity code-expiry for MCX. Maintain symbol-change, merger, delisting and contract-roll history.

### 30.5 Stage C4 - Temporal Normalization

Store separately:

```text
event_time       when the economic event occurred
data_date        period represented by the report
published_at     official publication timestamp if known
observed_at      when TrendForge first saw the artifact
available_at     earliest conservative timestamp usable by a scan
effective_from   when a rule/action becomes active
revised_at       when a correction became known
```

`available_at` controls backtests and ML. File naming dates do not automatically equal publication time.

### 30.6 Stage C5 - Domain Invariants

Examples:

```text
low <= open/close <= high
volume, OI and quantity >= 0
0 <= MWPL/delivery/holding percentages <= allowed domain maximum
option price >= intrinsic minus tolerance
expiry > quote timestamp for active contract
buy/sell side belongs to known enum
post holding approximately equals pre holding plus signed transaction
AMFI scheme totals pass workbook tolerance
```

### 30.7 Stage C6 - Deduplication

Build a source-specific natural event key. Exact duplicates collapse; conflicting duplicates remain as separate revisions. Cross-posted NSE/BSE/SEBI copies link to one canonical event family and do not create extra confidence.

### 30.8 Stage C7 - Corporate-Action Adjustment

Create versioned split/bonus/rights adjustment factors for price, volume and holdings. Dividends are handled according to return type. Any scan mixing adjusted and unadjusted series is rejected.

### 30.9 Stage C8 - Cross-Source Reconciliation

Compare authoritative overlaps:

```text
NSE vs BSE filing identity and event fields
cash close vs futures spot reference
NSE/BSE deal copies
AMFI ISIN vs security master
MCX contract vs current specification
source report date vs publication calendar
```

Differences outside configured tolerance create a conflict record and block only the affected feature/gate. Values are not averaged into false precision.

### 30.10 Stage C9 - Quality Report

Every parse produces row counts, reject counts, null rates, duplicate rates, identity match rate, date range, min/max, invariant failures, reconciliation conflicts and schema hash. Baseline drift thresholds quarantine suspicious publications.

## 31. Point-In-Time Storage Model

### 31.1 Required Layers

```text
RAW       immutable source bytes and fetch manifests
NORMALIZED source-shaped typed rows with original-field lineage
CANONICAL reconciled instruments, events, candles, positions and actions
FEATURES  versioned point-in-time calculations at a declared cutoff
EVIDENCE  human-readable claim plus supporting row/artifact IDs
DECISIONS gates, conflicts, ranking, state, sizing and reasons
OUTCOMES  later labels, fills, MAE/MFE, target/stop and failure category
```

### 31.2 Tables To Add Or Strengthen

```text
source_artifacts
fetch_attempts
parser_runs
parser_row_rejections
data_quality_reports
instrument_master_versions
instrument_identity_history
corporate_action_factors
canonical_events
event_source_links
source_conflicts
candle_revisions
feature_sets
feature_values or typed feature-family tables
evidence_claims
evidence_claim_links
candidate_gate_results
candidate_rank_components
scan_universe_members
trade_intents
outcome_observations
dataset_manifests
model_registry
```

Large candles/features use partitioned Parquet plus DuckDB. SQLite remains the transactional catalog, lineage, job and decision store. A candidate stores IDs, not only copied JSON.

### 31.3 Required Keys

Every normalized or derived row must be traceable through:

```text
artifact_id -> parser_run_id -> normalized_row_id
normalized_row_id(s) -> feature_set_id
feature_set_id(s) -> evidence_claim_id
evidence_claim_id(s) -> gate_result_id -> candidate_id
candidate_id -> trade_intent_id -> outcome_id
```

## 32. Feature Engineering For Stock Selection

### 32.1 Data Reliability Features

```text
authority_weight
freshness_factor
schema_confidence
identity_match_confidence
reconciliation_confidence
coverage_ratio
independent_family_count
unknown_critical_count
```

Reliability is a gate and ranking modifier, never a substitute for market evidence.

### 32.2 Market Regime

Calculate trend, breadth, volatility, liquidity and participant positioning separately:

```text
index distance from 20/50/200-day averages
advance/decline and new-high/new-low breadth
percentage of universe above 20/50/200-day averages
India VIX level, percentile and change
index futures basis and participant positioning regime
gap/overnight global alignment
event and expiry mode
```

Output: `BULL_TRADEABLE`, `BEAR_TRADEABLE`, `RANGE_SELECTIVE`, `EVENT_RISK`, `NO_TRADE` with evidence and invalidation.

### 32.3 Sector Leadership

Use point-in-time constituents. Compute sector relative return versus Nifty over 1/5/20/60 sessions, breadth, volume participation, RS acceleration and RRG phase. A stock receives sector support only when the sector is leading or improving and the stock is among its true leaders, not merely because both rose one day.

### 32.4 Liquidity And Tradability

```text
median traded value 20/60 days
zero-volume and stale-print frequency
median spread and depth when live feed exists
trade count and median trade value
impact/slippage estimate for proposed quantity
price band/circuit distance
free-float/market-cap context where available
```

The candidate is rejected if the planned quantity cannot be exited under conservative participation limits.

### 32.5 Cause Features

Each event gets:

```text
event_type, direction, materiality, surprise, novelty
event_time, age, expected_duration, source authority
affected revenue/earnings/capacity/ownership fraction
whether price already discounted the event
```

No NLP sentiment alone can define direction. Deterministic event fields and subsequent price acceptance must agree.

### 32.6 Fundamental Repricing Features

For swing candidates, parse point-in-time NSE/BSE XBRL/results into comparable periods and calculate:

```text
revenue, EBITDA/operating profit and PAT growth: YoY and sequential
gross/operating/net margin level and change
EPS growth and dilution-adjusted share count
operating cash flow versus PAT and free-cash-flow direction
debt, interest coverage, working-capital and receivable/inventory stress
ROCE/ROE trend where inputs are complete
segment growth and concentration
order book/capacity guidance only when structured from the filing
auditor qualification, exceptional items and one-off normalization flags
```

Do not call a result an earnings surprise without a dated, licensed consensus source. Without consensus, describe only reported growth/change and the market's post-result acceptance. Financial values are adjusted for restatements and mapped to the period originally available at the scan cutoff.

Intraday event trades may use the fresh result as cause plus tape acceptance, but delayed balance-sheet quality cannot prove intraday buying. Swing `READY` requires minimum financial-integrity coverage or an explicit event-driven strategy that does not claim fundamental quality.

### 32.7 Sponsor Features

```text
insider transaction quality and personal capital at risk
deal notional as percentage of free-float/traded value
deal premium/discount and anchor acceptance
number of independent AMCs adding/reducing
buyback executed versus announced capacity
promoter holding/pledge direction
supply overhang remaining and absorption state
```

ESOP exercise, inter-se transfer and token transactions are not equivalent to open-market purchases.

### 32.8 Cash-Flow Features

```text
RVOL-TOD = cumulative volume now / median cumulative volume at same minute
delivery_z = current delivery % versus symbol/weekday history
avg_trade_value = traded value / number of trades
close_location = (close - low) / max(high - low, tick)
effort_result = standardized volume / standardized true range
volume_above_vwap share when intraday prints are available
absorption/rejection around event anchor and AVWAP
```

Large volume with poor price progress is distribution/absorption evidence depending on location and follow-through, not automatically bullish.

### 32.9 Derivatives Features

```text
oi_change = current OI - comparable prior OI
basis = futures - synchronized spot
basis_percent = basis / spot
annualized_carry with days to expiry
rollover_ratio = next-expiry OI / total near-plus-next OI
OI quadrant with expiry/MWPL reliability
IV rank/percentile, skew and term structure
strike concentration and change, not static PCR alone
SLB fee/open-position percentile
```

Price up plus OI up is called long build-up only when MWPL/ban, contract roll, spot synchronization and basis behavior are reliable. Otherwise it remains unknown or conflicting.

### 32.10 Structure And Timing

Use adjusted candles and no-lookahead pivots for:

```text
trend and MTF alignment
relative-strength breakout
base/VCP contraction quality
ORB/VWAP/AVWAP acceptance
harmonic PRZ quality and lifecycle
distance from trigger in ATR units
overhead supply and low-volume pockets
wick, gap and failed-breakout traps
```

A harmonic pattern is one structure feature. It cannot overcome missing cause, sponsor/flow evidence, unsafe liquidity or stale official data.

### 32.11 Strategy-Specific Evidence Windows

| Mode | Primary evidence | Allowed delayed context | Evidence that cannot trigger alone |
| --- | --- | --- | --- |
| Intraday continuation | same-session cause, RVOL-TOD, VWAP/ORB, spread/depth, synchronized OI/basis/options | prior EOD delivery, monthly ownership as background | AMFI, quarterly holdings, old COT, static chart pattern |
| Intraday reversal | exhaustion/trap, failed anchor, breadth/index turn, derivatives reversal and liquidity | prior support/resistance and event anchors | oversold indicator or harmonic PRZ alone |
| Swing breakout | financial/event cause, sector leadership, daily/weekly structure, delivery/sponsorship and acceptance | AMFI/shareholding/CFTC according to scope | one intraday volume spike |
| Swing pullback | intact fundamental/sponsor thesis, trend/RS, low-supply pullback and reclaim | delayed ownership and sector regime | EMA touch alone |
| Event/PEAD | timestamped result/event, material change, gap/anchor acceptance and follow-through | historical financial quality | headline sentiment alone |

Each strategy has separate thresholds, decay, label horizon and backtest. Evidence from one mode cannot be reused with the wrong horizon merely to promote a candidate.

## 33. Evidence Construction And Conflict Logic

### 33.1 Evidence Claim Contract

Every positive or negative claim stores:

```text
claim_code and plain-language claim
direction: BULLISH / BEARISH / NEUTRAL / UNKNOWN
job: VETO / CAUSE / SPONSOR / FLOW / EXECUTION
independence_family
strength before quality adjustment
authority, freshness, scope and quality factors
supporting artifact/row/feature IDs
contradicting claim IDs
valid_from, valid_until and decay function
```

### 33.2 Quality Adjustment

For a claim `i`:

```text
q_i = authority_i * freshness_i * schema_i * identity_i * scope_i
effective_strength_i = raw_strength_i * q_i
```

Each factor is bounded `[0, 1]`. Missing critical factors produce `UNKNOWN`, not a guessed midpoint. Claims sharing an independence family are capped before aggregation.

### 33.3 Conflict Classes

```text
DATA_CONFLICT       authoritative sources disagree
TIME_CONFLICT       evidence belongs to different cutoffs
SCOPE_CONFLICT      index/regime data used as stock proof
DIRECTION_CONFLICT  cause/sponsor/flow point differently
PRICE_CONFLICT      price rejects event/deal/AVWAP anchor
REGIME_CONFLICT     stock setup fights market/sector regime
EXECUTION_CONFLICT  thesis valid but entry is late/illiquid
```

Critical data/scope conflicts block. Direction/price/regime conflicts downgrade to `WAIT` or `REJECT` according to severity and persistence.

## 34. Complete Stock Selection Funnel

### 34.1 Stage S0 - Build The Point-In-Time Universe

Start from the official active security master at the cutoff. Preserve delisted names for historical backtests. Classify equity, ETF, SME, surveillance, F&O and non-F&O; do not scan every series as an ordinary stock.

### 34.2 Stage S1 - Cheap Safety And Liquidity Prefilter

Before expensive calculations remove or mark:

```text
inactive/suspended/wrong series
ASM/GSM/operator restriction beyond policy
insufficient history
traded-value/spread/impact failure
unadjusted corporate action
stale or mixed-source candles
near circuit/price-band lock
```

This stage should reduce all NSE to a manageable research universe without using outcome-sensitive setup rules.

### 34.3 Stage S2 - Regime And Sector Allocation

Determine market state and rank sectors. Set allowed directions, maximum gross risk and number of candidates per sector. In `NO_TRADE`, calculations continue for research but executable candidates remain zero.

### 34.4 Stage S3 - Candidate Discovery

Use broad, cheap triggers:

```text
fresh material event
relative-strength acceleration
abnormal volume/value/trade-size
gap with cause
base/VCP/harmonic completion
deal/AVWAP reclaim
futures OI/basis change for F&O names
```

Discovery creates a candidate, not a recommendation.

### 34.5 Stage S4 - Evidence Enrichment

Fetch/join symbol-specific filings, deals, ownership, derivatives, SLB, anchors and event details only for discovered candidates. This staged join uses data efficiently and avoids hammering every source for every NSE symbol.

### 34.6 Stage S5 - Hard Gates

```text
G00 data integrity and cutoff
G01 active/eligible instrument
G02 market regime permits direction
G03 sector not hostile
G04 liquidity/impact passes
G05 surveillance/circuit/event safety passes
G06 structure exists and is no-lookahead
G07 trigger not stale/FOMO
G08 stop/invalidation is valid
G09 target and net R:R pass
G10 portfolio/correlation capacity passes
G11 emotional/daily safety passes
G12 cause/sponsor evidence sufficient for strategy type
G13 derivative evidence reliable when required/applicable
G14 source authority/freshness permits intended mode
```

`NOT_APPLICABLE` is distinct from pass. A non-F&O stock does not fail because it lacks futures OI, but it must meet stronger cash-flow/sponsor requirements.

### 34.7 Stage S6 - Block Scores, Not One Blind Score

Calculate separately:

```text
Cause          0-100
Sponsor        0-100
Cash Flow      0-100
Derivatives    0-100 or NOT_APPLICABLE
Structure      0-100
Regime/Sector  0-100
Execution      0-100
Data Quality   0-100
Trap Risk      0-100 where higher is worse
```

Strategy profiles define minimum blocks. Example swing breakout:

```text
Data Quality >= 90
Structure >= 75
Regime/Sector >= 60
at least one of Cause or Sponsor >= 65
Cash Flow >= 60
Derivative >= 55 when required, otherwise NOT_APPLICABLE
Execution >= 65
Trap Risk <= 30
all hard gates pass
```

The values above are initial research thresholds, not claimed edge. Walk-forward validation must calibrate them by setup, timeframe, regime and liquidity bucket.

### 34.8 Stage S7 - Ranking Among Valid Candidates

Only candidates passing the strategy's block minima enter ranking. A starting research rank is:

```text
rank = 0.15*Cause
     + 0.17*Sponsor
     + 0.18*CashFlow
     + 0.12*DerivativeOrNeutral
     + 0.18*Structure
     + 0.10*RegimeSector
     + 0.10*Execution
     - 0.20*TrapRisk
```

Then apply:

```text
rank *= DataQuality / 100
rank *= evidence_independence_factor
rank *= freshness_decay
rank -= unresolved_conflict_penalty
```

This rank orders valid opportunities; it does not itself create `READY` and must never be presented as win probability.

### 34.9 Stage S8 - State Assignment

| State | Exact meaning |
| --- | --- |
| `PRIORITY_RADAR` | Strong independent evidence; trigger not yet confirmed |
| `READY` | All required gates pass and current trigger/price/risk remain valid |
| `WAIT_DATA` | Required source missing, stale, conflicting or unparsed |
| `WAIT_TRIGGER` | Thesis valid; price trigger not reached |
| `WAIT_PULLBACK` | Valid thesis; entry quality poor or FOMO distance exceeded |
| `WAIT_EVENT` | Binary event/release/expiry risk inside lock window |
| `WAIT_EMOTIONAL` | User safety cooldown blocks execution |
| `REJECT` | Thesis, structure, liquidity, safety or R:R failed |
| `NO_TRADE` | Environment blocks new positions |
| `LOCKED_NO_TRADE` | Daily/user hard lock; no output can override |

Each state must identify the single next fact or event that can change it and the next evaluation time.

## 35. Quantity And Risk Utilization

Confidence cannot create risk. It can select only a pre-approved lower tier after every hard gate passes.

For the INR 1,00,000 account, preserve current research caps:

```text
70-79 calibrated confidence: probe risk 0.25% = INR 250
80-89 calibrated confidence: normal risk 0.50% = INR 500
90+ exceptional and validated: maximum 0.75% = INR 750
daily soft stop: 1.00% = INR 1,000
daily hard lock: 1.50% = INR 1,500
maximum open positions: 3, further reduced by correlation
```

`confidence` must eventually be a calibrated out-of-sample probability/quality tier for the exact setup bucket, not the raw rank.

```text
risk_per_unit = abs(entry - stop) + expected_slippage + fees
raw_quantity = floor(permitted_risk / risk_per_unit)
final_quantity = min(raw_quantity, lot_cap, liquidity_cap, margin_cap,
                     portfolio_cap, sector_cap, event_cap)
```

Rules:

1. missing invalidation/stop means quantity zero;
2. R:R below the validated setup threshold means reject;
3. averaging down is disabled;
4. a later entry never inherits the original quantity without recalculation;
5. correlated Gold/Silver, sector peers or multiple index-sensitive trades share one risk budget;
6. confidence cannot override daily, event, source or emotional locks.

## 36. Efficient Computation Strategy

Do not recompute every feature for every symbol on every tick.

```text
Layer A: daily universe/safety/liquidity materialization
Layer B: rolling EOD features updated only for changed partitions
Layer C: intraday cheap features for liquid universe
Layer D: expensive harmonics/options/filing enrichment only for discoveries
Layer E: active-candidate incremental updates on new bars/events
Layer F: full evidence bundle and risk calculation only near trigger
```

Cache keys include source artifact hash, parser version, adjustment version, feature version, instrument identity version and cutoff. Any dependency change invalidates only affected partitions.

Initial performance targets for the local machine:

```text
EOD all-NSE prefilter: <= 10 minutes after required files are available
EOD enriched shortlist: <= 20 minutes total
intraday liquid-universe update: complete before next bar interval
active candidate update: <= 5 seconds after normalized bar/event availability
API candidate read p95: <= 250 ms from materialized decision rows
zero overlapping scheduler runs
```

These are acceptance targets to benchmark and revise, not current measured claims.

## 37. ML, Backtest And Learning Without Leakage

### 37.1 Dataset Row

Every candidate state, including rejection, stores:

```text
cutoff and strategy/timeframe
point-in-time universe membership
all feature values and availability timestamps
data/source/parser/adjustment/feature versions
gate and conflict results
rank components and state reason
entry/stop/targets and proposed quantity
later MAE/MFE, target/stop/timeout and realized costs
```

### 37.2 Labels

Use multiple objective labels rather than one `WIN/LOSS`:

```text
triggered within validity window
target before stop
net return after modeled/actual costs
MAE and MFE in R units
time to trigger/target/stop
gap/slippage at entry
thesis invalidation category
maximum favorable move before failure
```

### 37.3 Validation

```text
walk-forward by calendar time
purged/embargoed splits for overlapping labels
survivorship-free point-in-time universe
publication-lag simulation
corporate-action and symbol-history correctness
regime, liquidity and setup stratification
calibration curve and Brier score
precision/recall for READY and false-positive rate
expectancy, drawdown and risk-of-ruin after costs
```

ML may calibrate rank, identify failure clusters and recommend threshold reductions. It cannot remove hard safety gates or autonomously increase maximum risk. Champion promotion requires shadow evidence; degradation automatically returns to deterministic baseline.

## 38. Failure Cases That Make A Screener Useless

| Failure | Required behavior |
| --- | --- |
| Current page serves yesterday's file | Detect `data_date`; show stale; block affected gate |
| File corrected after first publication | Save both revisions; new scans use revision; old decisions remain reproducible |
| Same event appears on five sites | Link one event family; count once |
| Missing value parsed as zero | Reject row/feature as unknown |
| Symbol changed or company merged | Resolve by effective-dated ISIN history |
| Split creates fake breakout/volume | Rebuild adjusted series and invalidate old feature cache |
| Participant OI interpreted as stock FII | Scope test fails and gate blocks |
| OI falls during expiry roll | Require near/next rollover before classification |
| Option chain timestamps differ from spot | Reject surface/Greeks for that cutoff |
| High volume is distribution | Use candle location, follow-through and anchor acceptance |
| Delayed AMFI/CFTC used before release | Point-in-time join excludes it |
| Anti-bot/login HTML saved as report | MIME/magic/schema quarantine |
| One unavailable source stops whole platform | Block only dependent gates; preserve unrelated research |
| All-source score hides critical failure | Hard-gate state remains visible and dominant |
| Backtest knows future index constituents | Use effective-dated universe snapshots |
| Bot receives old READY | Expiring intent plus broker-side revalidation rejects it |

## 39. Implementation Slices In Correct Order

### Slice D1 - Source Contract And Inventory Mapping

Files:

```text
source_registry.py or source_catalog.py
source_contracts.py
freshness_policy.py
tests/fixtures/source_contracts/
```

Work: convert the 209-link registry into machine-readable source families, roles, allowed jobs, artifact contracts, cadence and replacement rules. Reference/secondary URLs cannot enter gate dependencies.

Acceptance: every active decision field maps to one primary source contract or is explicitly `UNAVAILABLE`; every URL maps to a role; no orphan gate dependency.

### Slice D2 - Fetch/Archive/Revision Engine

Files:

```text
source_resolver.py
source_scheduler.py
artifact_store.py
storage.py migrations
tests/test_fetch_archive.py
```

Acceptance: retry-safe immutable downloads, revision detection, archive replay, size/MIME/magic checks, disk guard and failure audit pass with fixtures and controlled live smoke tests.

### Slice D3 - Identity, Calendar And Corporate Actions

Build security/contract masters, symbol history, calendars and adjustment factors before broad feature work.

Acceptance: known symbol changes, split/bonus/right examples, expiry and special-session fixtures reproduce expected adjusted rows.

### Slice D4 - Official Cash EOD Foundation

Implement NSE/BSE UDiFF/bhavcopy, delivery, trade count/value and reconciliation. Create all-NSE daily/weekly research universe and liquidity features.

Acceptance: manual sample reconciliation, completeness thresholds, all-NSE EOD prefilter benchmark and no unofficial READY.

### Slice D5 - Safety Sources

Implement ASM/GSM/suspension, price bands, MWPL/ban and event calendar. These are cheap and should run before expensive candidate enrichment.

Acceptance: current/effective-date tests and hard-gate behavior for every safety state.

### Slice D6 - Events And Smart Money

Implement announcements/actions, deals, PIT/SAST/pledge, buybacks/open offers and AMFI deltas with event dedupe, quality grading, anchors and supply states.

Acceptance: one event mirrored across sources contributes once; delayed data cannot appear early; price acceptance changes the claim state correctly.

### Slice D7 - F&O And Options

Implement contract master, futures tape, synchronized spot, OI/basis/rollover, SLB, then OpenAlgo/licensed option chain and locally verified IV/Greeks.

Acceptance: all quadrant/expiry/MWPL/basis/IV numerical and timestamp-failure fixtures pass.

### Slice D8 - Selection Funnel And Explanations

Files:

```text
universe_builder.py
candidate_discovery.py
evidence_engine.py
conflict_engine.py
selection_engine.py
rank_engine.py
reason_engine.py
```

Acceptance: deterministic replay from artifact IDs to state; block scores and hard gates visible; reasons identify cause, sponsor, confirmation, risk, conflict and next check.

### Slice D9 - EOD Shadow Scanner

Run all-NSE EOD scans, save all states, compare subsequent outcomes and manually audit top/false candidates. Do not start all-universe live intraday here.

Acceptance: 30 trading days with no false executable state, reproducible runs, measured runtime/completeness and reviewed false-positive clusters.

### Slice D10 - Intraday OpenAlgo Data And Bot Boundary

After user provides OpenAlgo contract, add legal live candles/quotes, active-candidate updates, expiring intents, paper/shadow mode, broker revalidation and kill switch.

Acceptance: feed outage, stale quote, reconnect, duplicate intent, partial fill, price-band, margin, daily lock and restart tests pass before explicit live enablement.

### Slice D11 - MCX Families

Build separately after shared acquisition/quality infrastructure: Gold Mini first, then Crude/NG, base metals and agriculture. Each family has distinct mandatory context and event locks.

## 40. Test And Audit Matrix For This Plan

### 40.1 Parser Golden Tests

For every schema version: raw official sample, expected normalized rows, reject rows, quality report and snapshot hash. Manually verify selected rows against the source document.

### 40.2 Property Tests

Generate column order changes, malformed numbers, duplicate rows, boundary percentages, future dates, archive bombs, timezone edges, split factors, option intrinsic violations and OI roll combinations.

### 40.3 Point-In-Time Replay Tests

Choose historical cutoffs and assert that no artifact, constituent, filing, CFTC/AMFI report, confirmed pivot or revision after the cutoff appears.

### 40.4 Decision Metamorphic Tests

```text
making a required source stale cannot improve state
adding a duplicate mirror cannot improve confidence
increasing trap evidence cannot improve rank
worsening spread/slippage cannot increase quantity
moving entry farther past trigger cannot improve execution
removing a hard veto is necessary but not sufficient for READY
```

### 40.5 Adversarial Market Replays

Test gap-and-fade, result IV crush, expiry rollover, promoter sale with temporary bounce, bulk-deal trap, low-float circuit move, split-adjustment breakout, sector divergence, index reversal and source outage during trigger.

### 40.6 Human Audit Sample

For each shadow run inspect:

```text
top 10 ranked
all READY
10 WAIT near promotion
10 REJECT near threshold
all source/data conflicts
all unusually large proposed quantities
later false positives and missed large moves
```

## 41. Completion Metrics

The data/selecting-stock milestone is complete only when:

```text
100% of gate-affecting sources have explicit artifact/schema/freshness contracts
100% of candidate claims link to exact source/feature IDs
100% of scans persist the point-in-time universe and cutoffs
zero reference/secondary/unofficial-only executable READY states
zero duplicate event-family confidence inflation in tests
zero known lookahead in replay suite
all critical source and corporate-action failures fail closed
EOD all-NSE runtime and completeness targets are measured and met
30-trading-day shadow run has no false executable-state defect
rank and confidence are clearly separated
calibration/backtest report includes costs and regime/liquidity breakdown
bot payload contains expiry, blockers, source cutoff and deterministic quantity proof
```

The first implementation action under this replacement plan is Slice D1: turn the canonical source registry into machine-readable source/artifact/job contracts and produce a coverage report showing exactly which stock-selection fields are available, unavailable, stale, fixture-only or live-verified.

## Full Historical Verbatim Appendix

The following source documents are embedded verbatim so no historical requirement, example, reasoning note or audit statement is lost. These appendices are historical evidence; the active sections above control implementation when statements conflict.

<!-- HISTORICAL_SOURCE_BEGIN path=REVIEW.md sha256=70a882bac2b0297c58cbbf3659afdec98a63b6e729e1b12c2c002e72d3d6be0a lines=318 -->
# TrendForge Review

Date: 2026-07-06

## Milestone Reviewed

Real harmonic scan slice:

- temporary yfinance OHLCV adapter.
- guarded nsepython/nselib/openchart source adapter surface.
- SQLite candle storage.
- Parquet candle store.
- source authority/freshness registry.
- exact NSE 4H custom builder.
- multi-sensitivity pivot engine.
- pivot deduplication and quality score.
- full initial harmonic ratio validator table.
- weighted hybrid quality score.
- G00-G14 gate scorer.
- lifecycle and alert generation.
- benchmark and chart overlay payload endpoints.
- pyharmonics attempt path plus deterministic internal ABCD fallback.
- harmonic pattern storage.
- harmonic pattern outputs saved into ML snapshots.
- frontend Real Harmonic Scan panel plus Advanced Gates status surface.

## Self-Critique

Potential bottlenecks:

- yfinance is temporary, unofficial, rate-limited, and not suitable for production trading.
- all-symbol NSE scanning is not implemented yet; current scan is symbol/timeframe on demand.
- pyharmonics output is attempted, but the current trade card uses the guarded internal fallback result because external library output shape needs deeper adapter hardening.
- Parquet exists now, but bulk all-NSE intraday scans still need batching, retention policy, and incremental cache invalidation.
- openchart and nselib are adapter surfaces only in this machine because those packages are not installed.
- G00-G14 exists, but smart-money, OI/MWPL/basis, sector, and momentum probes still return UNKNOWN until real adapters are implemented.

Required tests:

- browser interaction test for the Real Harmonic Scan panel.
- mocked yfinance failure test at API level.
- all-timeframe scan test for 30m, 1h, 4h, 1d, 1w.
- no-lookahead validation test for harmonic pivots.
- ratio validator fixture tests for every pattern family.
- frontend browser test for Advanced Gates button and chart overlay.
- future outcome-labelling test after ML export is added.

Assumptions:

- yfinance is allowed only as temporary prototype data.
- READY must remain blocked until smart-money and OI/MWPL/basis adapters are real.
- local-only SQLite storage is acceptable for the current stage.
- Parquet files are acceptable for local prototype candle storage.
- optional source adapters must fail closed until packages/schemas are verified.

## Requirement Coverage

Met:

- OHLCV adapter added.
- source registry added.
- Parquet store added.
- NSE 4H custom builder added.
- multi-sensitivity pivot engine added.
- pivot dedupe and pivot quality added.
- initial full ratio validator table added.
- weighted hybrid score added.
- G00-G14 gate scorer added.
- lifecycle/alerts added.
- benchmark and chart overlay payload added.
- candles stored.
- pyharmonics detector path added.
- pattern outputs saved into ML snapshots.
- volume and VWAP gates calculated.
- smart-money and OI/MWPL/basis gates block READY until real adapters exist.
- frontend shows real scan output as WAIT/REJECT.
- frontend shows source/parquet status and advanced gate summary.

Not fully met yet:

- live smart-money adapter.
- live OI/MWPL/futures basis/IV adapter.
- all-NSE background scheduler.
- production broker/licensed data feed.
- real NSE holiday download.
- daily liquidity source for volume/value/market cap/ASM/GSM.
- real frontend candle overlay drawing.

## Security Review

Three failure risks:

- public data source changes schema or rate-limits requests.
- malformed symbol/timeframe requests could cause noisy API failures if validation is expanded incorrectly.
- ML snapshots can grow without retention limits.
- Parquet files can grow without retention limits.

Two optimizations:

- add request-level caching for recent OHLCV fetches.
- batch candle inserts and use per-symbol scan queues for all-NSE scans.
- move pivot results to a pivot_cache table after the interfaces settle.

One security flaw:

- CORS currently allows all origins for local convenience. Before exposing outside localhost, restrict origins and add authentication.

## Required Next Fixes

1. Add raw-source archive table for downloaded files.
2. Install/configure and verify nselib/openchart only if source use is approved.
3. Add official NSE/AMFI/BSE/SEBI smart-money adapters.
4. Add NSE OI/MWPL/futures basis/IV adapters.
5. Add all-NSE scanner scheduler with rate limits.
6. Add ML export and outcome-labelling workflow.
7. Draw real XABCD/PRZ/targets on the frontend chart.

## Source Freshness Monitor Review

Added:

- official/free source catalog for NSE, BSE, AMFI, SEBI, MSEI, RBI, MCA, MCX, CFTC, WGC, and temporary wrappers.
- `source_snapshots` storage with HTTP status, content hash, content length, Last-Modified, ETag, raw snapshot path, and NEW/UNCHANGED/CHANGED/BROKEN/SKIPPED state.
- controlled source monitor scheduler with status, run-once, start, and stop endpoints.
- frontend Freshness status cell.
- false-change guard for dynamic HTML pages where raw hash changes but Last-Modified and content length are stable.

Remaining risks:

- URL reachability does not mean the data parser is complete.
- Dynamic official pages still need source-specific report-date parsing.
- Official websites can block automation; this must downgrade source state, not crash scanning.
- Scheduler is off by default to avoid excessive official-site requests.

Additional required fixes:

8. Add parser fixture tests for each official report adapter.
9. Add stale-source gate test so scanner blocks READY when required source freshness is BROKEN/STALE.
10. Add raw-source retention policy.
11. Add authentication before any non-local exposure.

## Source Parser And Gate Readiness Review

Added:

- `source_parse_results` table.
- source parser endpoint for latest raw snapshots.
- CFTC COT metadata parser that extracts report/data links but does not yet claim position-level COT data.
- generic metadata parser for official sources where structured report parsing is pending.
- `/api/gates/readiness` to explain G12/G13/MCX dependency status.
- `nselib` installation and adapter schema support for comma-formatted NSE EOD price fields.
- fail-closed openchart handling after package install did not return usable RELIANCE candles.

Failure cases handled:

- no raw source snapshot returns `WAIT_SOURCE_SNAPSHOT`.
- skipped source freshness check returns `WAIT_FETCH_REQUIRED`.
- broken source returns `BROKEN`.
- metadata-only parser output cannot pass READY.
- nselib comma-formatted prices are normalized before candle conversion.
- openchart installed but no data means controlled FAIL, not a fake candle stream.

Tests added:

- source parser waits without snapshot.
- CFTC parser extracts report links from a synthetic raw snapshot.
- gate readiness blocks READY without structured parsers.
- nselib-style `OpenPrice`/`ClosePrice` comma schema converts to candles.

Current test count:

- Backend: 24/24 PASS.
- Frontend: 55/55 PASS.

Remaining parser work:

- CFTC position-level parser for Managed Money, Commercials, and percentiles.
- AMFI monthly/scheme-wise holdings parser.
- NSE participant OI, MWPL, SLB, F&O bhavcopy parser.
- NSE/BSE deal and corporate-action parsers.

## Structured Parser Slice Review - 2026-07-08

Added:

- `backend/trendforge_api/parsers/` package with pure snapshot parsers.
- common parser helpers for CSV/ZIP/text rows, date extraction, numeric normalization.
- source freshness helper for internal `data_date` windows.
- NSE MWPL parser with SAFE/YELLOW/ORANGE/BANNED classification.
- NSE participant OI parser with `AGGREGATE_CONTEXT_ONLY` scope.
- NSE large deals parser with stock-level deal anchors.
- AMFI parser with `SWING_CONFIRMATION_ONLY` scope.
- CFTC parser that parses direct COT rows and keeps HTML source pages as metadata-only.
- MCX bhavcopy parser with `MCX_EOD_CONFIRMATION` scope.
- gate readiness now requires structured state, record count, and fresh `data_date`.
- tests for structured parser success, stale blocking, metadata-only blocking, and scope labels.

Self-critique:

- Parsers are fixture-proven and fail-closed, but not yet proven against every current official production file variant.
- They parse saved raw snapshots only; source-specific direct download resolvers are still required.
- Structured parser output is saved in `source_parse_results.output_json`, but row-level domain tables are not added yet.
- CFTC percentile logic is not implemented yet; current CFTC output gives net positioning, not 52-week percentile.
- AMFI month-over-month deltas are not implemented yet.
- NSE SLB, BSE buyback/open offer, SEBI PIT/SAST, and MCA/RBI parser extraction remain pending.

Requirement coverage:

- Fail-closed behavior: met for parser dispatch and gate readiness.
- No fake READY: met; missing, metadata-only, stale, empty, and broken sources block.
- Source scope enforcement: met for participant OI, AMFI, CFTC, and MCX.
- Future ML traceability: partial; parser result payloads are saved, but dedicated row tables and scanner run persistence remain pending.

Security/reliability review:

- Failure risk 1: official schemas may differ; add captured real-file fixtures before trusting production values.
- Failure risk 2: internal date extraction may fall back to Last-Modified when files lack content dates; source-specific date resolvers are still needed.
- Failure risk 3: large parser payloads in SQLite JSON can grow; row tables and retention are needed.
- Optimization 1: cache parsed rows by source hash to avoid reparsing unchanged snapshots.
- Optimization 2: add row-level indexes for symbol/date lookups.
- Security flaw: no authentication and permissive local CORS remain; do not expose outside localhost.

Verification:

- Python compile: PASS.
- Backend tests: 28/28 PASS.
- Frontend static checks: 57/57 PASS.
- Live `http://127.0.0.1:8001/api/health`: PASS.
- MCX bhavcopy parser.

## Source Resolver / Raw Archive / Scheduler Review - 2026-07-08

Added:

- direct official download resolver candidate layer in `source_resolver.py`.
- resolver-aware source monitor fetch path.
- `raw_source_archive` table with resolved URL, hash, local path, source state, and parser state after parse.
- row-level domain tables for MWPL, participant OI, large deals, AMFI holdings/deltas, CFTC COT positions, and MCX bhavcopy.
- CFTC official headerless `f_disagg.txt` positional parser for Gold/Silver/Crude/Copper/NG rows.
- fail-closed scanner scheduler with manual run-once and interval start/stop/status endpoints.
- scanner run/candidate persistence.
- frontend parser drilldown grid with parser results, row previews, archive previews, and manual guarded scanner run.

Self-critique:

- Resolver URLs are candidate paths, not permanent contracts. Official sites can change archive naming, require cookies, rate-limit, or return HTML instead of data.
- The scheduler is now wired, but the all-universe market scan still uses the prototype candidate engine until a licensed/live data feed and universe provider are connected.
- `amfi_stock_deltas` is currently a placeholder aggregation, not a true month-over-month holdings delta engine.
- CFTC row storage saves net positioning, but 52-week percentile and crowding percentile are still pending.
- Real options IV/Greeks, futures basis, and live OI still require source adapters beyond this slice.

Requirement coverage:

- direct source resolver: met as guarded resolver candidate system.
- raw archive: met.
- row-level tables: met for the six first parsers.
- scanner scheduler: met as fail-closed local scheduler, not production feed scanner.
- frontend parser drilldown: met.
- no fake READY: met by downgrading scanner candidates to `WAIT_SOURCE_CONFIRMATION` when gates are not confirmable.

Required tests:

- real official-file fixture tests for each resolver output variant.
- large-file parser performance tests.
- scanner interval start/stop race test.
- raw archive retention and dedupe tests.
- parser row-table migration compatibility test against older DBs.

Security/reliability review:

- Failure risk 1: official source anti-bot protection may break direct downloads. The system must record BROKEN/metadata-only and block READY.
- Failure risk 2: dynamic HTML source pages can change hashes without new data. Parser data-date remains the authority for gates.
- Failure risk 3: raw archive and scanner candidates can grow unbounded without retention policy.
- Optimization 1: skip parsing when source hash already has a completed parser result.
- Optimization 2: add symbol/date indexes as row tables grow.
- Security flaw: API is still local/open with permissive CORS; do not expose outside localhost until auth and restricted origins are implemented.

Verification:

- Python compile: PASS.
- Backend tests: 30/30 PASS.
- Frontend acceptance checks: 62/62 PASS.
- JavaScript syntax check: PASS.

## Source Contract / Replacement Map / Gate Artifact Review - 2026-07-08

Added:

- `source_contracts.py` with deterministic fail-closed unlock helpers.
- `source_parser_outputs` table to normalize parser state into `STRUCTURED_OK`, `STRUCTURED_STALE`, `PARSED_EMPTY`, `PARSED_METADATA_ONLY`, `SCHEMA_MISMATCH`, and blocking states.
- `source_freshness_status` table with latest data date, freshness flag, parser output ID, and reason.
- `gate_decisions` table and scanner-run persistence for G12/G13/MCX gate decisions.
- `source_replacement_map` table to preserve rejected/reference-only sources as controlled roles instead of deleting them.
- API endpoints for parser outputs, freshness status, gate decisions, and source replacement map.
- frontend parser drilldown additions for source role, normalized parser-output status, freshness, and unlock ability.

Self-critique:

- Gate decisions are saved at scanner-run level, not yet linked by ID on every scanner candidate row.
- Parser outputs are stored in SQLite only; Parquet artifact output path is not implemented yet.
- Source replacement map is seeded statically; it does not yet have an admin editor.
- `can_unlock_ready` is available as a deterministic helper, but existing scanner candidates still come from prototype/mock candidate generation.

Requirement coverage:

- Source role matrix: met.
- Replacement map: met.
- Parser-output artifacts: met.
- Freshness-status artifact: met.
- Gate-decision persistence: met for scanner runs.
- No fake READY: preserved; reference/unofficial/delayed/metadata-only sources cannot unlock READY.

Verification:

- Python compile: PASS.
- Backend tests: 31/31 PASS.
- Frontend acceptance checks: 65/65 PASS.
- JavaScript syntax check: PASS.
<!-- HISTORICAL_SOURCE_END path=REVIEW.md sha256=70a882bac2b0297c58cbbf3659afdec98a63b6e729e1b12c2c002e72d3d6be0a -->

<!-- HISTORICAL_SOURCE_BEGIN path=TREND_FORGE_AUDIT_ARCHIVE.md sha256=8749acee90c63d629d1b6fec6436dd6c9a2c78168e5b15e3019ede81fb0c44f5 lines=1726 -->
# TrendForge Audit Archive

This file preserves the reasoning history, gap analysis, and future-reference notes.

Merged from:

- ASSESSMENT_RADAR_UPGRADE_PLAN.md
- CONFLUENCE_ENGINE_UPGRADE_PLAN.md
- BUILD_BIBLE_GAP_ANALYSIS.md

The source files were archived as BACKUP_REFERENCE files in $backupDir.

---

## Source 1: ASSESSMENT_RADAR_UPGRADE_PLAN.md

# TrendForge Assessment Radar Upgrade Plan

This file preserves the latest assessment as a standalone merge record.

It does not replace `SCREENER_RULES.md` or `DASHBOARD_EXPERIENCE_PLAN.md`. It records the new radar, screen, and risk requirements that were merged into those files.

## 1. Merge Rule

Nothing from the older plan is deleted.

The following remain active:

- local web dashboard
- FastAPI backend
- SQLite database
- 8-screen daily workflow
- Layer 0 to Layer 8 screening pipeline
- 28-point CAUSE/SPONSOR/STRUCTURE/FLOW causal score
- 16-point live execution score
- options/GEX logic
- trap hard-gates
- data confidence rules
- risk engine
- journal and replay
- no automatic order placement in v1

## 2. Architecture Decision

The v1 build remains:

```text
Local browser dashboard + FastAPI backend + SQLite database
```

Reason:

- Better than single HTML because TrendForge needs live data, source health, alerts, history, options, and journaling.
- Better than full cloud for v1 because cloud adds security, deployment, and credential complexity before logic is validated.
- Local read-only app is safer for the first build.

## 3. Score Clarification

The radar must not show two unexplained scores like:

```text
INFY 23/28 + 14/16
```

Correct display:

```text
Stage 1 Pre-Market: ELIGIBLE 23/28
Stage 2 Live: CONFIRMED 14/16 -> READY
```

Stage 1 decides whether the stock deserves attention. Stage 2 decides whether the live entry is valid now.

## 4. Forced Counterparty Definitions

Forced counterparty must be shown as a named flag.

Examples:

- OTM options near expiry going to zero: gamma squeeze or pinning possible.
- High short interest plus stop cluster above resistance: forced short covering.
- Promoter pledge near danger zone: forced margin-call selling.
- MF/ETF redemption pressure: DII selling even in fundamentally good stocks.
- FII hedge/currency unwind: false banking or index breakout risk.
- Index inclusion/exclusion: passive forced buying or selling.

Output example:

```text
FORCED COUNTERPARTY: HIGH
Reason: promoter pledge 68 percent; margin-call selling zone approaching.
Impact: downgrade long setup or reject if price starts cascading.
```

## 5. NO_TRADE Environment

NO_TRADE is a primary output, not a fallback.

The system must be able to say:

```text
TODAY: NO_TRADE ENVIRONMENT
Reason: VIX spike, weak breadth, major event nearby, and unstable pre-open direction.
Action: no fresh trades. Reassess at 10:30 AM.
```

Triggers:

- India VIX spike
- breadth worse than 1:3
- RBI/Fed/budget/election/war shock
- GIFT Nifty or index futures reversing repeatedly
- no sector leadership
- RED data confidence
- expiry mechanics overpowering normal trend

## 6. Delivery Percent Timing

Delivery percent is T+1 data.

Correct display:

```text
Delivery: 48 percent (yesterday, T+1 data)
Live proxy: RVOL-TOD 3.2x + OI change + VWAP behavior
```

Delivery can support sponsor context. It cannot be treated as live institutional confirmation.

## 7. Liquidity Time Window Filter

TrendForge must understand NSE intraday liquidity.

| Time IST | State | Rule |
| --- | --- | --- |
| 9:15 to 9:30 | opening volatility | observe and build ORB |
| 9:30 to 10:00 | first valid window | ORB/gap triggers allowed |
| 10:00 to 11:30 | clean momentum | best normal entry window |
| 11:30 to 1:00 | lunch trap | suppress new entries unless RVOL-TOD > 3.0x |
| 1:00 to 2:30 | resume window | trend resumption allowed |
| 2:30 to 3:15 | closing push | manage exits and expiry effects |
| 3:15 to 3:30 | closing mechanics | avoid fresh intraday entries |

Output example:

```text
WAIT_LOW_LIQUIDITY
Reason: signal fired at 11:45 AM during lunch trap; RVOL-TOD only 1.1x.
Action: wait for 1 PM retest or RVOL-TOD > 3.0x.
```

## 8. Gap Fade Counter-Setup

Gap scanner must detect both continuation and fade.

```text
GAP FADE WATCH
ADANIENT: +3.1 percent gap, no verified catalyst
Setup: if price fails below pre-open low in first 15 minutes -> SHORT for gap fill
Target: previous close
Invalidation: reclaim opening range high with RVOL-TOD > 2.0x
```

The app must journal actual gap-fill performance instead of trusting a fixed probability forever.

## 9. Expiry Mode

Expiry logic must be based on the actual NSE contract calendar and contract master.

Current planning assumption:

- NIFTY weekly/monthly option expiry is Tuesday under current NSE specifications.
- Do not hardcode old Thursday assumptions.
- If NSE changes expiry rules later, the contract data must drive the UI.

Expiry Mode must show:

- active expiry date
- days to expiry
- max pain
- OI walls
- IV rank
- expected move
- gamma flip
- GEX regime
- pin risk
- squeeze risk
- IV crush risk

## 10. RRG Sector Rotation

Sector heatmap is not enough. Add rotation state.

```text
SECTOR RRG STATUS
IT: Leading -> buy setups allowed
Banking: Improving -> early accumulation watch
Metals: Lagging -> avoid longs or short watch
FMCG: Weakening -> reduce long aggression
```

States:

- Leading
- Improving
- Weakening
- Lagging

## 11. Portfolio Correlation Risk

The risk engine must detect same-bet exposure.

```text
CORRELATION WARNING
Open positions: INFY Long, HCLTECH Long, TCS candidate
Theme: all IT
Portfolio correlation: 0.85+
Effective risk: 3x single-trade risk
Action: block new TCS or reduce size.
```

Small-account default:

```text
Account: INR 1,00,000
Risk: 0.5 percent = INR 500
Max positions: 2 to 3 unless settings are changed
```

## 12. Operator Activity Hard-Block

India-specific operator activity must block trades.

Hard-block patterns:

- price up 10 to 15 percent in 3 days, no verified news, delivery below 15 percent
- repeated circuits without catalyst
- penny stock below INR 20 with 50x to 100x RVOL
- SME stock suddenly liquid without institutional evidence
- low float plus sudden breakout and poor delivery
- ASM/GSM or surveillance list

Operator block overrides all technical scores.

## 13. Crisis And Scenario Panel

The top bar must show crisis/regime override.

```text
REGIME OVERRIDE: RED
Scenario: RBI shock / Fed shock / war / recession / election / budget
Instruction: no fresh trades until volatility and breadth stabilize.
```

## 14. Options Deep Dive

Add a dedicated options screen for F&O stocks.

Required:

- IV rank
- IV percentile where available
- OI walls
- change in OI
- volume concentration
- expected move
- max pain
- GEX and gamma flip
- delta, gamma, theta, vega
- estimated-versus-source Greek badge
- optimal strike selector
- event straddle pricing
- pin/squeeze warning
- IV crush warning

## 15. Two-Week Event Calendar

Show forward risk:

```text
RBI policy: in 4 days
TCS result: in 2 days
NIFTY expiry: in 3 days
MSCI rebalance: in 12 days
```

Events must affect readiness state, size, option IV risk, swing decisions, and NO_TRADE.

## 16. Cross-Market Driver Row

Stock cards must show driver alignment.

```text
TATASTEEL
Driver: LME copper -2 percent, China PMI missed
Impact: driver against long setup
Action: downgrade to WAIT unless stock-specific sponsor is strong.
```

## 17. Funnel View

Live Radar must show survival by layer.

```text
Universe: 1800
Tradable after hard filters: 400
Regime/sector aligned: 120
Causal pass: 18
Live confirmed: 5
READY: 2
WAIT: 3
REJECT: 115
```

The funnel may recommend strict/normal/exploratory profiles, but it must not silently loosen thresholds.

## 18. System Health

System Health must show:

- NSE feed freshness
- options chain freshness
- delivery data date
- FII/DII data date
- event calendar freshness
- database status
- last scanner run
- stale source warnings

## 19. Settings

Settings must let the user change:

- account capital
- risk percent
- maximum open positions
- sector cap
- correlation cap
- data credentials/API keys
- Telegram token
- refresh interval
- strict/normal/exploratory profile
- intraday/swing defaults

## 20. Swing Manager

Swing Manager must show:

- original thesis
- daily rescore
- thesis intact/broken
- event risk
- sector/RRG change
- trailing stop path
- P&L in R
- exit reason

## 21. Journal Accuracy And Equity Curve

Journal must calculate:

- equity curve
- daily P&L
- win rate by setup
- expectancy by score bucket
- market-bias accuracy
- sector-call accuracy
- score above 20 win rate
- score below 15 win rate
- REJECT saved-loss rate
- NO_TRADE day result
- replay mode result

Example percentages in the plan are placeholders until real journal data exists.

## 22. Final Screen List

```text
0   System Health + Regime Override Bar
1   Evening Prep
2   Morning Brief
3   Pre-Open Scanner
4   Live Radar + Shortlist
5   Stock Deep Dive
5b  Options Deep Dive
6   Position Sizing
7   Trade Monitor
7b  Swing Manager
8   Journal + Learning + Equity Curve
9   Event Calendar
10  Settings
```

Embedded:

- Why Rejected tab
- WAIT Board
- Funnel View
- Replay Mode
- Data Confidence badge
- Breadth Danger Alarm
- Forced Counterparty card
- Cross-Market Driver row

## 23. Build Order After This Assessment

1. Backend skeleton: FastAPI, SQLite, settings, health endpoint.
2. Data pipelines: NSE, FII/DII, delivery, bulk/block, corporate actions, options chain, event calendar, sector indices, cross-market drivers.
3. Screening engine: hard filters, 8 layers, causal score, operator blocks, gap scanner, trap detection.
4. Intraday radar: execution score, RVOL-TOD, liquidity window, gap fade, expiry mode, OI/options confirmation.
5. Frontend: Screen 0 to Screen 10, embedded radar panels, NO_TRADE display.
6. Risk and journal: sizing, correlation, small-account rules, equity curve, replay, system accuracy.
7. Validation: stale data, no silent threshold relaxation, expiry calendar, operator hard-blocks, score separation.

## 24. Trader Safety And Emotional Emergency Layer

This is a mandatory upgrade after the emergency-support review.

TrendForge must protect the user from emotional trading, revenge trading, panic trading, and account damage. This layer sits above normal scoring.

Final safety principle:

```text
If market evidence is weak, WAIT.
If data is stale, WAIT or REJECT.
If risk is too high, NO_TRADE.
If the user is emotionally unsafe, LOCKED_NO_TRADE.
Capital protection comes before opportunity.
```

## 25. Safety States

Required states:

- LOCKED_NO_TRADE
- DAILY_STOP_HIT
- COOLDOWN_ACTIVE
- WAIT_EMOTIONAL_RISK
- WAIT_RECOVERY_REVIEW
- BROKER_DATA_TRAUMA
- STOP_TRADING_NOW

These states can override READY.

## 26. Panic Mode

Add a visible panic button.

```text
PANIC MODE ACTIVE
New trades: LOCKED
Existing positions: risk management only
Cooldown: 30 minutes
Required before unlock: recovery checklist
```

Rules:

- block all new trades
- keep open positions visible
- allow only risk reduction
- journal the event
- require cooldown before unlock

## 27. Daily Loss Circuit Breaker

Default planning values:

- warning at -1.0R
- lock at -1.5R
- lock after 2 consecutive full-stop losses
- lock after configured account percent loss

Example:

```text
DAILY LOSS LIMIT HIT
Loss: -1.5R
State: LOCKED_NO_TRADE
Action: no new trades for today
```

## 28. Revenge Trading Detector

Detect:

- trade attempted quickly after loss
- size increased after loss
- repeated direction switching
- trading during NO_TRADE
- chasing after missed trigger
- stop widened or cancelled
- too many trades in one day

Output:

```text
WAIT_EMOTIONAL_RISK
Reason: new trade attempted 4 minutes after a full-stop loss and size increased by 2x.
Action: blocked for cooldown.
```

## 29. Pre-Trade Emotional Checklist

Before sizing, ask:

```text
Am I chasing?
Am I trying to recover a loss?
Did I miss the original entry?
Is this trade inside today's plan?
Is the stock READY, not WAIT or REJECT?
Can I accept the stop-loss without changing it?
```

Unsafe answers change the state to WAIT_EMOTIONAL_RISK.

## 30. Confidence Versus Evidence

Panel:

```text
CONFIDENCE VS EVIDENCE
User confidence: HIGH
System evidence: LOW
State: WAIT
Reason: emotion is stronger than data.
```

User confidence never increases score.

## 31. Market Trauma Modes

Required modes:

- FLASH_CRASH_MODE
- DATA_OUTAGE_MODE
- BROKER_OUTAGE_MODE
- VIX_SHOCK_MODE
- NEWS_PANIC_MODE
- GAP_TRAP_PANIC_MODE
- LIMIT_CIRCUIT_MODE

These modes can block new trades and show risk-only handling for existing positions.

## 32. Emergency Support Boundary

TrendForge is not a medical or crisis-support service.

If the user indicates extreme distress, inability to stop, self-harm thoughts, or unsafe behavior:

```text
STOP_TRADING_NOW
State: LOCKED_NO_TRADE
Action: step away from the screen and contact trusted support or local emergency help.
```

The app must not provide therapy. It must stop trading activity.

## 33. Safety Journal

Every safety event must store:

- timestamp
- safety state
- trigger
- realized P&L
- unrealized risk
- attempted trade
- open positions
- cooldown duration
- override attempt
- next allowed action

## 34. Safety Settings

Settings must include:

- daily max loss in R
- daily max loss as account percent
- max trades per day
- max consecutive losses
- cooldown after loss
- panic-lock duration
- manual override allowed/disallowed
- small-account strict mode
- emotional checklist always-on
- broker/data outage behavior

Default v1 rule:

- no manual override for hard safety locks.

## 35. Open-Source Tools To Evaluate

Useful open-source candidates:

| Area | Candidate | Use |
| --- | --- | --- |
| Fast backtesting | vectorbt | many-rule backtests |
| Event replay | Backtrader | candle-by-candle replay |
| Indicators | TA-Lib, ta, pandas-ta-classic | common indicators |
| Options Greeks | py_vollib, mibian | IV and Greeks |
| Portfolio risk | Riskfolio-Lib, skfolio | risk contribution and correlation |
| Analytics | QuantStats | equity curve and drawdowns |
| Calendars | exchange_calendars | sessions and holidays |
| Local analytics | DuckDB | fast scans |
| Fast dataframes | Polars | high-speed transforms |
| Charts | TradingView Lightweight Charts, Apache ECharts, uPlot | financial charts |
| Tables | AG Grid Community | scanner grid |
| NSE adapters | nselib, jugaad-data, NseIndiaApi, nsepython | data adapters behind fallbacks |

Rules:

- verify license and maintenance before implementation
- keep every data library behind an adapter
- unofficial NSE adapters need fallbacks and freshness checks
- local Greeks must be labeled ESTIMATED
- backtests must be point-in-time and avoid lookahead bias

## 36. Updated Build Order With Safety

1. Backend skeleton: FastAPI, SQLite, settings, health endpoint.
2. Data pipelines: market data, events, options chain, cross-market drivers.
3. Screening engine: hard filters, causal score, operator blocks, trap detection.
4. Safety engine: daily loss circuit breaker, cooldowns, panic lock, revenge detector, safety journal.
5. Intraday radar: execution score, liquidity window, gap fade, expiry mode.
6. Frontend: Screen 0 to Screen 11, safety bar, panic lock, recovery screen.
7. Risk and journal: sizing, correlation, equity curve, replay, safety analytics.
8. Validation: stale data, no silent thresholds, expiry calendar, operator blocks, safety lock tests.

## 37. Confluence Engine Audit Merge

This section records the later audit that identified missing professional confirmation details.

The update is now mandatory for future implementation.

Files updated:

- `SCREENER_RULES.md`: core confluence engine rules.
- `DASHBOARD_EXPERIENCE_PLAN.md`: command bar and stock-card display.
- `ASSESSMENT_RADAR_UPGRADE_PLAN.md`: this audit record.
- `CONFLUENCE_ENGINE_UPGRADE_PLAN.md`: standalone future reference.

## 38. Audit Results Preserved

Status after audit:

| Point | Status Before Merge | Final Action |
| --- | --- | --- |
| OI quadrant logic | partial | add standalone named states |
| MWPL/F&O ban risk | missing | add reliability gate before OI |
| futures basis/cost of carry | missing | add basis layer |
| rollover data near expiry | partial | add expiry/rollover interpretation |
| options IV confirmation | partial | add IV + OI confluence |
| deal price anchor | missing | add live anchor monitoring |
| event AVWAP | partial | add AVWAP from event dates |
| smart-money quality grading | missing | classify ESOP, open-market, transfer, pledge, sale |
| volume quality metrics | partial | add trade count, average trade size, volume location |
| SLB borrow proxy | missing/unclear | add short-pressure proxy where available |
| participant-wise OI scope | needed clarification | label as index/regime context only |
| confluence truth table | missing | add named state machine |
| Screen 0 command bar | missing | add persistent command bar |
| emotional safety as gate | already added, now reinforced | keep as Layer 9 gate |
| FOMO lock after big gap | missing | add ATR-distance downgrade |
| supply overhang tracking | partial | track remaining seller holding and absorption |

## 39. New Named Output States

Required states after this audit:

- PRIORITY_RADAR
- READY
- WAIT
- WAIT_FOMO
- WAIT_EMOTIONAL
- WAIT_OI_UNRELIABLE
- WAIT_BASIS_CONFLICT
- WAIT_SUPPLY_OVERHANG
- REJECT
- SHORT_WATCH
- NO_TRADE
- LOCKED_NO_TRADE
- STOP_TRADING_NOW

These states replace simple score-only final output.

## 40. 10-Layer Engine After Audit

```text
Screen 0: Command Bar
Layer 0: Global Macro Gate
Layer 1: Market Regime Gate
Layer 2: Sector Gate
Layer 3: Stock Safety Filter
Layer 4: Smart Money Layer
Layer 5: OI + Volume + Basis Layer
Layer 6: Setup Identification
Layer 7A: Price Acceptance And Anchor Layer
Layer 8: Risk Engine
Layer 9: Emotional Safety Gate
Layer 10: Execution And Post-Entry
```

Layer 7A and Layer 9 are mandatory.

## 41. Confluence Matrix Requirement

The final decision must combine:

- smart money quality
- OI quadrant
- MWPL reliability
- futures basis
- rollover
- IV + options OI
- volume quality
- deal anchor
- event AVWAP
- supply overhang
- FOMO distance
- portfolio risk
- emotional safety

Minimum matrix examples:

| Condition | State |
| --- | --- |
| strong smart money + long build-up + institutional volume + rising premium + anchors accepted | PRIORITY_RADAR |
| bullish smart money + short covering only | READY with sustainability warning |
| bullish OI but MWPL above 90 percent | WAIT_OI_UNRELIABLE |
| bullish price/OI but negative falling basis | WAIT_BASIS_CONFLICT |
| price more than 1x ATR past ideal entry | WAIT_FOMO |
| motivated seller still owns large stake | WAIT_SUPPLY_OVERHANG |
| daily loss or safety lock active | LOCKED_NO_TRADE |

## 42. Future Implementation Rule

Future implementation must not simplify this audit into:

```text
score >= threshold = buy
```

The correct behavior is:

```text
named state + reason + evidence + conflict explanation + next valid action
```

No READY state is valid unless:

- hard gates pass
- MWPL allows OI interpretation
- price acceptance is valid
- risk is defined
- trader safety is GREEN
- no unresolved conflict requires WAIT


---

## Source 2: CONFLUENCE_ENGINE_UPGRADE_PLAN.md

# TrendForge Confluence Engine Upgrade Plan

This file exists so future implementation does not forget the professional confirmation layer.

It is a standalone reference for the Smart Money + OI + Volume + Basis + Price-Acceptance engine.

## 1. Purpose

TrendForge must not mark a stock important only because one signal is strong.

The final radar must answer:

```text
Did smart money act?
Was the signal high quality?
Did price accept the smart-money level?
Did volume confirm with institutional quality?
Did OI confirm the same direction?
Is OI reliable after MWPL and expiry checks?
Is futures basis supportive?
Are options IV/OI confirming or warning?
Is the trade late/FOMO?
Is there supply overhang?
Is the trader safe to act?
```

## 2. Pages Updated

This requirement is stored in:

- `SCREENER_RULES.md`: section 46.
- `DASHBOARD_EXPERIENCE_PLAN.md`: sections 46 to 63.
- `ASSESSMENT_RADAR_UPGRADE_PLAN.md`: sections 37 to 42.
- `CONFLUENCE_ENGINE_UPGRADE_PLAN.md`: this standalone file.

## 3. What Was Missing Before

The audit found these missing or partial items:

- OI quadrant was partial, not a named per-stock state.
- MWPL proximity was missing before OI interpretation.
- Futures basis and cost of carry were missing.
- Rollover interpretation was mentioned but not built.
- IV rank existed, but IV + OI behavior was missing.
- Deal price anchor was missing.
- Event AVWAP was not built as a mechanism.
- Smart-money quality grading was missing.
- Volume quality metrics were partial.
- SLB borrow proxy was missing.
- Participant-wise OI scope needed clarification.
- Conflict matrix was missing.
- Screen 0 command bar needed to be persistent.
- Emotional safety needed to remain a gate before execution.
- FOMO lock after overextended move was missing.
- Supply overhang tracking was partial.

## 4. 10-Layer Decision Engine

```text
Screen 0: Command Bar
Layer 0: Global Macro Gate
Layer 1: Market Regime Gate
Layer 2: Sector Gate
Layer 3: Stock Safety Filter
Layer 4: Smart Money Layer
Layer 5: OI + Volume + Basis Layer
Layer 6: Setup Identification
Layer 7A: Price Acceptance And Anchor Layer
Layer 8: Risk Engine
Layer 9: Emotional Safety Gate
Layer 10: Execution And Post-Entry
```

Layer 7A and Layer 9 are mandatory.

## 5. Screen 0 Command Bar

Always visible:

```text
System: GREEN
Regime: TRADEABLE BULLISH
India VIX: Normal
Breadth: 1.8:1 Positive
Expiry Mode: OFF
MWPL Watch: SAFE
Liquidity Window: ACTIVE
Trader Safety: GREEN
NO_TRADE Override: OFF
```

The Command Bar can downgrade every stock card.

## 6. OI Quadrant

| Price | OI | State | Meaning |
| --- | --- | --- | --- |
| up | up | LONG_BUILD_UP | fresh longs entering |
| up | down | SHORT_COVERING | shorts exiting |
| down | up | SHORT_BUILD_UP | fresh shorts entering |
| down | down | LONG_UNWINDING | longs exiting |

Rule:

- LONG_BUILD_UP is more sustainable than SHORT_COVERING.
- OI quadrant must be shown on every F&O stock card.

## 7. MWPL Reliability Gate

MWPL must be checked before OI.

| MWPL Usage | State | Action |
| ---: | --- | --- |
| below 80 percent | SAFE | normal OI interpretation |
| 80 to 90 percent | YELLOW | caution |
| 90 to 95 percent | ORANGE | OI unreliable |
| above 95 percent | RED/F&O BAN | do not trust fresh OI signal |

State:

```text
WAIT_OI_UNRELIABLE
```

## 8. Futures Basis / Cost Of Carry

```text
basis = futures_price - spot_price
```

Strong confirmation:

```text
price up + OI up + basis premium rising = strongest long build-up
```

Conflict:

```text
price up + OI up + basis discount/falling = WAIT_BASIS_CONFLICT
```

## 9. Rollover Logic

Near expiry:

| Current Expiry OI | Next Expiry OI | Read |
| --- | --- | --- |
| falling | rising | position carried forward |
| falling | flat/down | position closing |
| rising | rising | aggressive late build-up |
| falling fast | not checked | do not interpret until rollover checked |

Expiry Mode changes OI interpretation.

## 10. IV + OI Confluence

| Options Behavior | State |
| --- | --- |
| call buying + IV rising + call OI rising | DIRECTIONAL_CALL_BUYING |
| put buying + IV rising + put OI rising | PUT_BUYING_PRESSURE |
| OI rising + IV falling | WRITING_PINNING |
| IV spike both sides | EVENT_FEAR_STRADDLE |
| high IV before event | IV_CRUSH_WARNING |

IV rank alone is not enough.

## 11. Deal Price Anchor

Every important transaction creates an anchor.

Anchor examples:

- FII bulk deal price
- MF block deal price
- CEO/promoter open-market buy price
- promoter/PE/co-founder sale price
- result-day anchor
- breakout trigger

States:

- ANCHOR_ACCEPTED
- ANCHOR_TEST
- ANCHOR_BROKEN

If a bullish deal anchor breaks with rising sell volume, downgrade or reject.

## 12. Event AVWAP

Track AVWAP from:

- insider buy date
- bulk/block deal date
- result day
- breakout day
- policy/order announcement day
- large sale day

Price above multiple event AVWAPs improves conviction.

Price below event AVWAP warns that the event is rejected.

## 13. Smart-Money Quality Grading

| Signal | Grade |
| --- | --- |
| CEO/promoter open-market buy | very strong |
| repeated promoter buys | very strong |
| FII/MF bulk deal at premium | very strong |
| high-quality block deal at market | medium/strong |
| token director buy | low |
| ESOP exercise/allotment | neutral |
| inter-se transfer | neutral |
| pledge release | positive |
| pledge addition | danger |
| promoter/PE/co-founder sale at discount | hard caution |

Do not score ESOP as open-market conviction.

## 14. Volume Quality

Required fields:

- RVOL-TOD
- traded value
- delivery percent with T+1 label
- bid-ask spread
- trade count
- average trade size
- average trade size change
- volume above/below VWAP
- volume near high/low
- candle close location
- spread-adjusted volume

Same raw volume can mean retail churn or institutional footprint. The system must distinguish it.

## 15. SLB Borrow Proxy

Use NSE SLB data where available as a short-pressure proxy.

Fields:

- borrow quantity
- lend quantity
- borrow rate
- rate change
- data freshness

High borrow rate plus breakout can mean squeeze potential.

If unavailable, show unavailable. Do not invent short interest.

## 16. Participant-Wise OI Scope

Participant-wise OI is index/regime context only.

Correct display:

```text
Participant OI: index/regime signal
Stock-level FII evidence: bulk deals, filings, FPI changes, delivery/RVOL proxy
```

Never claim participant OI proves FII buying in one stock.

## 17. Supply Overhang

Track large seller risk:

- seller identity
- seller type
- quantity/value sold
- remaining holding
- sale anchor price
- time since sale
- absorption evidence

States:

- SUPPLY_OVERHANG_HIGH
- SUPPLY_ABSORBED
- SUPPLY_REJECTION

If a motivated seller still owns more than 10 percent after a large sale, show supply risk until absorption is proven.

## 18. FOMO Lock

```text
if current_price > ideal_entry + 1x ATR:
    state = WAIT_FOMO
```

Output:

```text
WAIT_FOMO
Reason: price is too far past ideal entry.
Action: wait for VWAP retest, pullback, or next setup.
```

## 19. Final State Machine

Allowed final states:

- PRIORITY_RADAR
- READY
- WAIT
- WAIT_FOMO
- WAIT_EMOTIONAL
- WAIT_OI_UNRELIABLE
- WAIT_BASIS_CONFLICT
- WAIT_SUPPLY_OVERHANG
- REJECT
- SHORT_WATCH
- NO_TRADE
- LOCKED_NO_TRADE
- STOP_TRADING_NOW

The output must be a named state with reason, evidence, conflict explanation, and next action.

## 20. Confluence Matrix

| Smart Money | OI | Volume | Basis | Price Acceptance | State |
| --- | --- | --- | --- | --- | --- |
| strong | LONG_BUILD_UP | institutional | premium rising | above anchors | PRIORITY_RADAR |
| strong | SHORT_COVERING | strong | flat | above AVWAP | READY with sustainability warning |
| medium | LONG_BUILD_UP | decent | flat | above anchor | READY or WAIT |
| strong | LONG_BUILD_UP | weak | premium rising | too far past entry | WAIT_FOMO |
| strong | LONG_BUILD_UP | strong | negative/falling | below AVWAP | WAIT_BASIS_CONFLICT |
| weak ESOP only | LONG_BUILD_UP | high raw volume | premium | above anchor | WAIT |
| strong | any | any | any | MWPL above 90 percent | WAIT_OI_UNRELIABLE |
| bearish seller at discount | SHORT_BUILD_UP | high volume | discount | below anchor | REJECT or SHORT_WATCH |
| any | any | any | any | safety lock active | LOCKED_NO_TRADE |

## 21. F&O Versus Non-F&O Rule

F&O stocks:

- use OI, MWPL, futures basis, IV, options flow, rollover.

Non-F&O stocks:

- do not fake OI.
- use smart money, cash volume, delivery, AVWAP, anchors, supply, risk, and safety.

## 22. Data Storage Needed

Required tables:

- derivatives_oi_snapshots
- futures_basis_snapshots
- mwpl_snapshots
- rollover_snapshots
- iv_snapshots
- deal_anchors
- avwap_anchors
- volume_quality_snapshots
- slb_snapshots
- supply_overhang_events
- confluence_states

## 23. Testing Needed

Test:

- OI quadrant classification
- MWPL downgrade
- F&O ban block
- basis conflict
- rollover interpretation
- IV + OI flow type
- deal anchor accepted/broken
- AVWAP reclaim/rejection
- ESOP versus open-market buy
- trade count and average trade size
- SLB unavailable behavior
- participant OI scope
- WAIT_FOMO
- supply overhang
- LOCKED_NO_TRADE override

## 24. Implementation Principle

Never reduce this engine to:

```text
score >= threshold = buy
```

Correct final behavior:

```text
named state + evidence + conflict + next valid action
```

Capital protection and confirmation quality come before opportunity.


---

## Source 3: BUILD_BIBLE_GAP_ANALYSIS.md

# TrendForge Build Bible Gap Analysis

## Verification

Read and checked the attached Build Bible in these numbered ranges:

- lines 1-85: philosophy, causal framework, actor model, independence logic
- lines 86-170: data sources, fallback design, SQLite schema, data health, orchestrator order
- lines 171-255: macro, regime, sector, tradability, cause scoring
- lines 256-340: sponsor decay, Wyckoff, structure, flow, GEX, independence, trap gates, WHY generator
- lines 341-425: risk, slippage, portfolio correlation, exits, options depth, setup parameters, failure modes
- lines 426-503: remaining failure modes, skip-list, file plan, tests, daily workflow, start requirements

## What Was Already In The Old Plan

The old plan already had:

- NSE-first screener purpose
- 4-layer CAUSE/SPONSOR/STRUCTURE/FLOW scoring
- gated runtime sequence from macro to exit
- GIFT Nifty, FII/DII, sector, VIX, breadth, and options confirmation
- tradability filters like ASM/GSM, F&O ban, pledge, liquidity, market cap
- setup families: gap-and-go, ORB, VCP, 21 EMA pullback, PEAD, true relative strength
- RVOL-TOD, MTF, VWAP, OI, trap detection
- risk, position sizing, slippage, journal, backtest, dashboard, alerts

## What Was Missing Or Too Weak

The Build Bible added these missing or sharper rules:

1. Forced-counterparty analysis: every pick must ask who is forced to buy/sell and whether the trader is becoming the fuel.
2. Four trend causes: information asymmetry, forced flow, fundamental re-rating, reflexivity.
3. Six actor model: FII, DII, promoter/insider, named super-investor, market maker/option writer, retail/operator.
4. Top-decile universe gate: pass 3/4 layers is not enough; candidate should rank in the top 10 percent of today’s universe.
5. Exact gate thresholds: total score >= 18, CAUSE >= 2, SPONSOR >= 4, STRUCTURE >= 2, FLOW >= 2.
6. Exact SQLite schema for point-in-time data and backtests.
7. Data health states: GREEN, AMBER, RED with visible degradation.
8. Explicit staleness decay formula and lambda values.
9. Wyckoff effort-vs-result algorithm for hidden absorption.
10. GEX formula and gamma flip logic.
11. Cross-market driver mapping as a formal confirmation layer.
12. Independence penalty formula.
13. Trap hard-gates that cannot be overridden by score.
14. Eleven trap types with names and detection logic.
15. Reasoning generator clauses with source/date evidence.
16. Half-Kelly risk adjustment and risk clamp.
17. Portfolio correlation using 60-day returns, sector risk cap, total open risk cap.
18. Options depth: IV term structure, IV skew/risk reversal, 0DTE/expiry dynamics, premium concentration.
19. Extra modules: intraday_microstructure, swing_extras, options_depth, event_preposition, crowding, shorting_asymmetry.
20. Testing plan for traps, staleness, independence, source fallback, and point-in-time correctness.

## Big-Player / Less-Common Radar Data Added

These are the highest-value items common traders usually do not model well:

- promoter SAST and insider disclosures
- pledge and pledge-release risk
- named buyer/seller from bulk/block deals
- AMFI monthly holding deltas across schemes
- FII/DII cash plus derivative positioning
- FII index futures long/short ratio
- delivery percent anomaly, not just volume
- Wyckoff absorption bars: high volume with low price progress
- GEX and gamma flip
- options premium concentration by strike
- IV skew and IV term structure
- index inclusion/exclusion and passive flow pressure
- short squeeze fuel and days-to-cover where available
- cross-market drivers like crude, copper, DXY, USD/INR, Nasdaq
- high-volume-node/supply-zone trap checks
- narrow-index divergence: Nifty up but breadth weak

## How This Improves The Scanning Radar

The radar improves in five ways:

1. Earlier detection: it looks for information asymmetry, sponsor footprints, and absorption before price indicators confirm.
2. Better trap avoidance: it rejects operator pumps, weak delivery gaps, priced-in news, HVN breakouts, VWAP failures, and narrow-index rallies.
3. Better market alignment: it blocks setups when macro, regime, sector, or breadth are hostile.
4. Better flow detection: it uses RVOL-TOD, OI change, gamma/GEX, IV/skew, and premium concentration instead of plain volume.
5. Better survivability: it sizes by regime, score, half-Kelly, slippage, correlation, sector risk, and total open risk.

## Conflict Found And Resolved

The Build Bible says funnel telemetry can auto-loosen thresholds if output is below 3 candidates and auto-tighten if output is above 8.

That conflicts with the safety rule: do not silently relax filters to force trades.

Final decision added to `SCREENER_RULES.md`:

- funnel telemetry can recommend threshold changes
- it can show strict/normal/exploratory profiles
- it cannot silently loosen actionable-mode rules
- any threshold change must be visible in the UI

## Claims To Verify Later Against Official Sources

The Build Bible includes specific current broker/regulatory claims. They are useful planning assumptions, but they must be verified before implementation:

- Upstox current REST/WebSocket limits
- Upstox option Greeks availability and instrument caps
- Angel One endpoint behavior and limits
- NSE current endpoint paths and anti-bot behavior
- current SEBI and broker rules for any future auto-order execution

Until those are verified, TrendForge stays read-only plus alerts.

## Final Judgment

The Build Bible does improve the plan. The original rules had the skeleton. This document adds the institutional radar, exact math, data model, trap taxonomy, options depth, and implementation/test detail needed to build it without guessing.

---

## Source 4: Official Institutional Source Stack Audit

## Verification

Read and checked the three attached institutional-source inputs in these ranges:

- source stack file: lines 1-99, official-first hierarchy and missing source list.
- search/source file: lines 1-101, how to search SEBI, NSE, BSE, FII/DII, bulk deals, brokerage, institutional channels, EPFO, LIC, and MCX context.
- institutional intelligence report: lines 1-565, daily/monthly/quarterly source cadence, FII/DII flows, named investors, MF changes, bulk/block deals, brokerage calls, political disclosure limitations, MCX notes, and source priority.

## Honest Audit Result

The old plan had the right smart-money direction, but the official-source stack was not strong enough.

Already present:

- NSE/BSE bulk and block deal concept.
- FII/DII aggregate flow concept.
- insider/promoter filings concept.
- pledge and pledge-release risk.
- participant-wise OI scope warning.
- SLB borrow proxy concept.
- AMFI mentioned only lightly.

Missing or too weak:

1. AMFI monthly and scheme-wise portfolio disclosure was not treated as the official stock-level DII ground truth.
2. Mutual fund buying/selling was not separated into scheme-level breadth, AMC-level conviction, new entries, exits, and passive NAV drift.
3. NSE participant-wise F&O data was not listed as a saved official source URL in the stock source registry.
4. NSE SLB reports were not promoted into the official source stack with source health.
5. Buyback tender offer, takeover/open offer, and daily buyback execution sources were missing.
6. MSEI FII/DII page was missing even though combined exchange data was referenced.
7. RBI FPI monitoring was missing as a cap/caution/ban context source.
8. MCA SBO/charges were missing as a lower-priority hidden ownership and loan-against-shares context.
9. NSE corporate actions were missing as a mandatory adjustment source for AMFI deltas and price anchors.
10. Secondary sites were not explicitly blocked from scoring unless official confirmation exists.

## Why AMFI Is Critical

AMFI portfolio disclosure is the biggest upgrade.

Reason:

- aggregate DII flow says whether domestic institutions bought the market.
- AMFI holdings show which mutual fund schemes held which stocks.
- month-over-month AMFI deltas can identify stock-specific DII accumulation or distribution.
- scheme breadth matters: one fund buying is weaker than many schemes independently adding.
- AMFI is delayed, so it confirms swing/institutional sponsorship rather than intraday execution.

Radar rule added:

```text
If AMFI confirms multi-scheme accumulation:
    raise swing confidence and smart-money quality.

If AMFI shows broad distribution:
    downgrade rallies, even if intraday price looks strong.

If only aggregate DII flow is positive:
    use as market context only, not stock-level proof.
```

## Official Source Links Saved

The following user-provided and audited links must remain in the plan:

- [AMFI Monthly Portfolio Disclosure](https://www.amfiindia.com/online-center/portfolio-disclosure)
- [AMFI Scheme-wise Disclosure](https://www.amfiindia.com/otherdata/scheme-wise-disclosure)
- [NSE FII/DII](https://www.nseindia.com/reports/fii-dii)
- [NSE All Reports - Derivatives](https://www.nseindia.com/all-reports-derivatives)
- [NSE SLB Trading](https://www.nseindia.com/static/products-services/slbs-trading)
- [BSE Buyback Tender Offer](https://www.bseindia.com/markets/PublicIssues/FIS_BuybackTenderoffer.aspx)
- [BSE Takeover/Open Offer](https://www.bseindia.com/markets/publicissues/fis_takeover)
- [NSE Tender Offer Buyback](https://www.nseindia.com/static/products-services/tender-offer-buyback)
- [NSE Daily Buy Back](https://www.nseindia.com/companies-listing/corporate-filings-daily-buy-back)
- [NSE Corporate Actions](https://www.nseindia.com/companies-listing/corporate-filings-actions)
- [MSEI FII/DII Activities](https://www.msei.in/downloads/equity-reports/fii-dii-activities)
- [MCA Master Data](https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html)
- [RBI FPI Monitoring](https://www.rbi.org.in/Scripts/BS_FiiUSer.aspx)

## Source Priority Added

TrendForge must follow this trust order:

1. Official regulator/exchange/industry body: SEBI, NSE, BSE, AMFI, RBI, MCA, MSEI.
2. Official company/exchange filings: PIT, SAST, pledge, SHP, buyback, corporate actions.
3. Official exchange trade data: bulk/block deals, participant OI, SLB, FII/DII flows.
4. Secondary discovery tools: Trendlyne, StockEdge, Moneycontrol, Tickertape, InsiderScreener, screeners, brokerage summaries.

Secondary sources can discover ideas, but cannot promote a stock to READY without official confirmation.

## Scanner Improvement

This upgrade improves the radar in seven ways:

1. DII attribution becomes stock-specific through AMFI instead of only aggregate market-level flow.
2. Derivative positioning becomes clearer through NSE participant-wise F&O reports, while staying correctly scoped to regime/index context.
3. Short-pressure and squeeze risk get an official Indian proxy through SLB.
4. Buyback/open-offer events become anchor levels and support/control-change signals.
5. Corporate action adjustments prevent false AMFI holding changes after split, bonus, rights, merger, or demerger.
6. FPI limit monitoring prevents false bullish interpretation when foreign buying is constrained by sector caps.
7. Source health makes the system honest: stale, blocked, delayed, or secondary-only data cannot silently drive a trade call.

## Big-Player Data Added

The less-common institutional data now saved for future build:

- AMFI scheme-wise stock holding deltas.
- AMC breadth and scheme-count changes.
- NSE participant-wise F&O reports.
- NSE SLB lending/borrowing reports.
- daily buyback execution filings.
- BSE/NSE tender and open offer trackers.
- MCA SBO and charges context.
- RBI FPI sector-limit monitoring.
- corporate action adjustment feed.
- cross-exchange FII/DII completion using MSEI.

## Implementation Rule

Future code must implement source lineage.

Every signal needs:

```text
source_url
source_owner
source_type
trust_label
source_date
latest_data_date
parser_state
record_count
decision_use
```

If the system cannot read the source:

```text
Source state: RED or MANUAL
Do not pretend the signal exists.
Do not upgrade to READY from secondary-only evidence.
Show the exact missing source in the stock card.
```

## Final Judgment

This source-stack input materially improves the stock screener plan.

The most important missed item was AMFI stock-level mutual fund holdings. Without it, TrendForge could say "DII buying" only at market level and would be weak at stock-level DII attribution. With AMFI, participant OI, SLB, buyback/open offer, corporate actions, MSEI, RBI, and MCA added, the radar can track more institutional player behavior and avoid many false bull/bear conclusions.

---

## Source 5: Harmonic Screener Upgrade Audit

## Request

Add harmonic pattern screener for:

- 30 minute
- 1 hour
- 4 hour
- 1 day
- 1 week
- all NSE data

Also check whether external/open-source options are available.

## Honest Finding

External harmonic pattern detection options are available. The difficult part is not detecting Gartley/Bat/Crab style ratios. The difficult part is getting clean, legal, reliable NSE intraday OHLCV data for every symbol and timeframe.

## Open-Source / External Options Found

| Option | Use | Judgment |
| --- | --- | --- |
| pyharmonics | Python harmonic pattern search over OHLC dataframe | best prototype/reference candidate |
| HarmonicPatterns | Python harmonic pattern detection with completed/predicting modes | useful second reference, verify dependency burden |
| stock-pattern | CLI/library with harmonic patterns and backtesting | useful reference, but GPL-3.0 license needs care |
| TradingView open-source harmonic scripts | ratio and visual reference | not backend for all-NSE scanning |

## Data Source Decision

For all-NSE 30m/1h/4h/daily/weekly scans:

- official or licensed market data is required for production.
- daily bhavcopy is not enough for 30m/1h/4h.
- random scraping is not acceptable for a reliable screener.
- broker feeds may work for personal use, but limits and redistribution rules must be checked.

## 4H Candle Warning

NSE cash market has a 09:15-15:30 session.

Therefore:

```text
4H_CUSTOM_NSE_SESSION
Bar 1: 09:15-13:15
Bar 2: 13:15-15:30 partial bar
```

This must be labelled in UI. A fake 24-hour 4H candle model would create wrong pivots.

## Scanner Rule Added

Harmonic patterns are setup zones, not final trade calls.

Correct behavior:

```text
Pattern forming -> HARMONIC_WATCH_FORMING
Price in PRZ -> HARMONIC_PRZ_ACTIVE
Pattern plus confirmation -> HARMONIC_CONFIRMED
Pattern plus full TrendForge confluence -> READY / PRIORITY_RADAR
Pattern invalidated -> REJECT_INVALIDATED
```

## What This Improves

The harmonic scanner adds:

- early reversal-zone detection.
- multi-timeframe PRZ confluence.
- structured D-point invalidation and target planning.
- better swing watchlist formation.
- extra confirmation when harmonic PRZ aligns with AMFI/smart money, OI, VWAP, AVWAP, sector, and volume.

## Risk

False positives can be high if:

- data is poor.
- stock is illiquid.
- ZigZag pivot sensitivity is too loose.
- lower-timeframe pattern fights daily/weekly trend.
- harmonic pattern is treated as buy/sell without confirmation.

Final decision:

```text
Add harmonic screener.
Use external library only as detector/reference.
Keep TrendForge confirmation engine as final decision maker.
```

## External Harmonic Website Check

Additional harmonic scanner/software websites were checked and saved into the master plan.

Saved categories:

- open-source libraries: pyharmonics, HarmonicPatterns, stock-pattern.
- TradingView scanners: TRN Trading, Morning Starr, Trendoscope, open-source scripts.
- commercial harmonic scanners: Patterns Hunters, HarmonicPattern.com, HarmonicTrader, MotiveWave, ClickAlgo.
- India/NSE references: JustTicks, ChartAlert, Chartink, Investar.
- broader charting/scanner references: GoCharting, TrendSpider, MarketInOut.

Honest conclusion:

```text
Many harmonic screeners exist.
Most are useful for visual/reference scanning.
None should become the final TrendForge decision engine.
```

Reason:

- most tools do not combine official NSE/BSE/AMFI/source proof.
- most tools do not apply MWPL, OI, futures basis, SLB, IV, or smart-money filters.
- TradingView scanners have symbol/platform limits.
- commercial tools may not provide API/export access for all-NSE backend scanning.
- some India tools are EOD/daily-focused and may not cover 30m/1h/4h production scanning.

Final rule:

```text
External scanner says: pattern exists.
TrendForge asks: is the pattern confirmed by data, volume, source proof, market regime, risk, and safety?
```

## Hybrid Free No-Broker Harmonic Screener Audit - 2026-07-06

Input compared against current TrendForge harmonic plan and current implementation.

### Honest Verdict

The new input is best for engineering build order and failure-mode coverage. The current TrendForge plan is best for final trade safety because it already blocks READY unless market, sector, smart-money, OI/MWPL/basis, risk, and emotional gates agree.

Final decision: merge both. Use the new plan for data pipeline, session engine, pivot engine, ratio validation, scanner schedule, API shape, and dashboard detail. Keep TrendForge's existing final decision state machine and safety gates.

### Added To Master Plan

- source priority matrix: openchart-style 1m, jugaad-data, nselib/NSE bhavcopy, yfinance fallback, broker/licensed feed.
- raw 1-minute first, then resample derived timeframes.
- Parquet plus SQLite storage split.
- cache invalidation rules by source/timeframe.
- liquidity and data completeness pre-filter.
- NSE official calendar requirement.
- 4H_CUSTOM_NSE_SESSION boundary and partial-bar caution.
- multi-sensitivity ZigZag grid.
- pivot deduplication by price/time threshold.
- pivot quality score.
- internal ratio validator expansion for major harmonic families.
- deterministic gate scoring G00-G14.
- nine confirmation probes.
- NSE-aware scanner schedule.
- expanded harmonic API roadmap.
- anti-pattern list.
- hybrid build order from Phase 0 to Phase 6.

### Added To Dashboard Plan

- harmonic screener table columns.
- detail card fields for pivots, ratios, PRZ, gates, MTF map, final state, and next action.
- harmonic data health panel.
- harmonic scheduler status panel.

### Critical Correction

The input mentioned `MatrixSearch` for pyharmonics. Current installed pyharmonics exposes `HarmonicSearch`. Future implementation must feature-detect the pyharmonics API and should not hardcode one class name without verification.

### Still Not Built

- openchart-style 1-minute adapter.
- Parquet candle store.
- NSE calendar engine.
- liquidity pre-filter.
- multi-sensitivity ZigZag and dedup engine.
- full ratio validator table.
- G00-G14 scoring engine.
- nine confirmation probes.
- APScheduler jobs.
- full harmonic screener table UI.

## Master Implementation Plan v2.0 Harmonic Audit - 2026-07-06

Input compared against current TrendForge hybrid harmonic plan and current prototype.

### Honest Verdict

v2 is stronger for implementation sequencing, lifecycle tracking, weighted ranking, alerting, verification milestones, and license policy.

TrendForge's current hybrid plan remains stronger for final trade safety because it has data-health veto, named G00-G14 confirmation gates, smart-money, OI/MWPL/basis, market/sector, risk, and emotional safety integration.

Final decision: merge v2 additively. Use v2 quality score for ranking, not final readiness. Final READY remains controlled by TrendForge's full state machine.

### Added To Master Plan

- source insight summary from the 23+ tools.
- source authority plus freshness model: LIVE, CACHED, STALE, BROKEN.
- environment smoke tests before build expansion.
- universe modes: NIFTY50_SMOKE, NIFTY200_LIQUID, NIFTY500_PLUS_FNO, ALL_NSE_RESEARCH, WATCHLIST_ONLY.
- stricter intraday liquidity defaults.
- optional 5m/15m trigger timeframes.
- lifecycle states: FORMING, COMPLETE, TRIGGERED, INVALIDATED, WIN_T1, WIN_T2, WIN_T3, LOSS, EXPIRED.
- pattern trade levels including T3 and adaptive stop rule.
- weighted hybrid quality score for ranking only.
- alert engine roadmap.
- scan performance targets.
- backend module boundary target.
- phase verification table.
- harmonic module license policy.

### Added To Dashboard Plan

- lifecycle columns.
- quality score and gate ratio display.
- P/L state tracking.
- chart overlay requirement: candles, XABCD lines, PRZ, invalidation, targets, VWAP/AVWAP, volume highlight.
- alert center.
- explicit decision to keep the current FastAPI/local frontend instead of switching to Dash now.

### Rejected Or Modified From v2

- v2's simple `READY if 2 of 3 gates pass` rule is too weak. TrendForge keeps full gate model.
- v2's fixed 0.5 percent stop around X is too crude. TrendForge requires ATR/tick/spread/structure-aware stop buffer.
- v2's `MatrixSearch` naming is not safe to hardcode. Current installed pyharmonics exposes `HarmonicSearch`; implementation must feature-detect.
- Dash/Plotly is useful for chart ideas but should not replace the existing single-panel dashboard at this stage.

### Still Not Built

- Parquet store.
- source authority + freshness registry.
- nselib/openchart adapters.
- NSE calendar engine.
- strict liquidity pre-filter.
- lifecycle updater for TRIGGERED/WIN/LOSS.
- weighted hybrid score.
- alert center.
- chart overlay.
- performance benchmark tests.
- license audit table in runtime source registry.

## v2 Missing Feature Build Slice - 2026-07-06

User requested the v2 ideas previously marked "not built" to be added and made available as functions.

### Built In This Slice

- source registry table and `/api/sources/registry`.
- guarded `/api/sources/smoke-test` for yfinance, nsepython, nselib, openchart, static_csv.
- multi-source OHLCV dispatch in `/api/ohlcv/fetch`.
- Parquet candle store and endpoints: `/api/parquet/status`, `/api/parquet/write`, `/api/parquet/candles`.
- exact NSE 4H custom builder and `/api/nse/4h-custom/build`.
- multi-sensitivity ZigZag pivot engine.
- pivot deduplication and pivot quality score.
- ratio validators for Gartley, Bat, Butterfly, Crab, Deep Crab, Cypher, Shark, Five-0, ABCD, AB=CD.
- weighted hybrid quality score.
- G00-G14 gate scorer.
- lifecycle state: FORMING, COMPLETE, TRIGGERED, INVALIDATED, WIN_T1/T2/T3.
- harmonic alert storage and `/api/harmonic/alerts`.
- benchmark endpoint `/api/harmonic/benchmark`.
- chart overlay payload endpoint `/api/harmonic/chart-overlay`.
- frontend Advanced Gates button with source registry and Parquet status boxes.

### Still Guarded Or Incomplete

- nselib package is not installed locally, so adapter returns controlled unavailable state until installed/configured.
- openchart package is not installed locally, so adapter returns controlled unavailable state until installed/configured.
- smart-money/OI/MWPL/basis/sector/momentum gates exist as named gates but remain UNKNOWN until real adapters are built.
- exact frontend drawing of candles/XABCD/PRZ/targets is not yet implemented; backend now returns overlay payload.
- all-NSE scheduler is not built yet.

### Verification

Backend tests: 17/17 PASS.
Frontend static checks: 53/53 PASS.
Python compile: PASS.
Frontend JS syntax: PASS.

### Liquidity Pre-Filter Follow-Up - 2026-07-06

Added explicit liquidity pre-filter function and `/api/harmonic/liquidity-check` endpoint.

Current checks:
- 20-candle average volume.
- last price threshold.
- 20-candle average traded value.

Still unknown until official adapters are built:
- market cap.
- ASM/GSM surveillance status.

Verification updated: backend tests 18/18 PASS.
<!-- HISTORICAL_SOURCE_END path=TREND_FORGE_AUDIT_ARCHIVE.md sha256=8749acee90c63d629d1b6fec6436dd6c9a2c78168e5b15e3019ede81fb0c44f5 -->

<!-- HISTORICAL_SOURCE_BEGIN path=TREND_FORGE_LINE_BY_LINE_AUDIT_2026-07-07.md sha256=ced274be886ce7372ec06b25eb77f372349fa3dcf8fc3ec0d756c9d0dea398b9 lines=385 -->
# TrendForge Line-By-Line Build Audit

Date: 2026-07-07

## Honest Verdict

The v2 missing-feature slice is implemented and validated for the guarded local prototype.

It is not production-perfect yet. Several items are available as safe functions/endpoints but still depend on missing packages, official data feeds, or future adapters before they can become live trading truth.

## Validation Run

```text
Backend tests: 18/18 PASS
Python compile: PASS
Frontend JS syntax: PASS
Frontend static checks: 53/53 PASS
Live server: http://127.0.0.1:8001/api/health PASS
```

## Fresh Revalidation - 2026-07-07

Commands/results verified after the latest user question:

```text
Backend tests with PYTHONPATH=D:\TrendForge\backend: 18/18 PASS
Python compile for backend modules: PASS
Frontend JS syntax: PASS
Frontend static checks: 53/53 PASS
Live server: 127.0.0.1:8001 LISTENING
Main DB: D:\TrendForge\data\trendforge_research.db exists
Parquet status: available, 2 files, 183 rows
Harmonic source registry: 25 saved source/reference links
```

Live data/storage check:

```text
POST /api/ohlcv/fetch RELIANCE 1d 6mo yfinance:
  PASS
  candleCount: 125
  savedCount: 60
  trustLevel: UNOFFICIAL_TEMP

GET /api/ohlcv/candles RELIANCE 1d:
  PASS
  saved candles returned from local SQLite

POST /api/harmonic/scan RELIANCE 1d useStored=true:
  PASS as no-false-positive behavior
  result: no valid harmonic ratio in latest pivot structure
  patterns: []
  savedMlRunId: null because no valid pattern was found

Pattern persistence/ML snapshot path:
  PASS in backend test `test_harmonic_stored_scan_saves_pattern_and_ml_snapshot`
  controlled synthetic pattern creates harmonic output, saves it, creates savedMlRunId, and saves harmonic ML candidates
```

Current main DB counts after live verification:

```text
source_registry: 6
ohlcv_candles: 125
harmonic_patterns: 0
ml_scan_runs: 1
ml_scan_candidates: 5
harmonic_alerts: 3
```

Important interpretation:

The main DB has zero `harmonic_patterns` right now because the latest real RELIANCE scan did not find a valid harmonic pattern. This is correct. It should not create fake pattern rows. The save path is still tested and working when a valid pattern exists.

Live endpoint timing sample:

| Endpoint | Result | Approx Latency |
| --- | --- | ---: |
| /api/health | PASS | 156 ms |
| /api/sources/registry | PASS | 16 ms |
| /api/parquet/status | PASS | 8 ms |
| /api/harmonic/liquidity-check?symbol=RELIANCE&timeframe=1d | PASS | 7 ms |
| /api/harmonic/advanced/analyze?symbol=RELIANCE&timeframe=1d | PASS | 40 ms |
| /api/harmonic/benchmark?symbol=RELIANCE&timeframe=1d | PASS | 10 ms |
| /api/harmonic/chart-overlay?symbol=RELIANCE&timeframe=1d | PASS | 13 ms |
| /api/harmonic/alerts?symbol=RELIANCE | PASS | 7 ms |
| /api/sources/smoke-test?source=openchart | CONTROLLED FAIL | 16 ms |

## Feature Audit

| Requested Feature | Current Status | Evidence | Working Quality | Gap / Reason |
| --- | --- | --- | --- | --- |
| openchart 1-minute adapter | Installed but guarded | `source_adapters.py`, `/api/sources/smoke-test` | Controlled unavailable response works | Superseded 2026-07-08: package installed, RELIANCE returned no usable candles, keep fail-closed |
| nselib adapter | Installed and verified | `source_adapters.py`, source registry | RELIANCE 1d returned 255 candles | Superseded 2026-07-08: installed and schema-normalized |
| nsepython adapter | Implemented for daily/weekly | `source_adapters.py` | Package installed; adapter code exists | Live NSE response still depends on NSE site/wrapper behavior |
| Parquet candle store | Built | `parquet_store.py`, `/api/parquet/status`, `/api/parquet/write` | Live status: available, 1 file, 58 rows | Retention policy and partition strategy not production-grade yet |
| Source authority + freshness registry | Built | `source_registry` table, `/api/sources/registry` | Live registry returns 6 sources | Raw source archive table still pending |
| Exact NSE 4H custom builder | Built | `nse_session.py`, `/api/nse/4h-custom/build` | Unit test verifies 2 bars/day | Needs official NSE holiday/calendar integration |
| Liquidity pre-filter | Built, partial official coverage | `liquidity_prefilter`, `/api/harmonic/liquidity-check` | RELIANCE live check passed | Market cap and ASM/GSM remain unknown until official adapters exist |
| Multi-sensitivity ZigZag 5/8/13 | Built | `build_multi_sensitivity_pivots` | Advanced analysis returns pivots | Needs more fixture validation across known patterns |
| Pivot deduplication | Built | `_dedupe_alternating` and group merge logic | Covered indirectly by advanced endpoint test | More edge-case tests needed |
| Pivot quality score | Built | consensus + volume + wick model | Advanced endpoint returns quality values | Retest/isolation scoring still basic |
| Full ratio validator table | Built initial version | `RATIO_TABLE` | Returns top validations | Needs textbook fixture tests for every pattern family |
| Gartley/Bat/Crab/Cypher/Shark/5-0 validator | Built initial version | `validate_harmonic_ratios` | Present in code | Some complex patterns need deeper Carney-specific edge tests |
| Weighted hybrid quality score | Built | `hybrid_quality_score` | RELIANCE returned 0.592 | Ranking only; not final READY authority |
| G00-G14 gate scorer | Built | `score_gates` | RELIANCE returned gateRatio 0.28 | Several gates are `UNKNOWN` until real smart-money/OI/sector/momentum adapters exist |
| Pattern lifecycle TRIGGERED/WIN/LOSS | Built initial lifecycle | `lifecycle_state` | RELIANCE returned COMPLETE | Needs background updater to progress saved patterns over time |
| Alert center | Built backend + small frontend status | `harmonic_alerts`, `/api/harmonic/alerts` | Alerts persisted for RELIANCE | Full in-app alert center UI still basic |
| Performance targets/benchmarks | Built single-symbol benchmark | `/api/harmonic/benchmark` | RELIANCE benchmark passed | Full universe benchmark not possible until scanner exists |
| Chart overlay with XABCD/PRZ/targets | Backend payload built | `/api/harmonic/chart-overlay` | Endpoint returns candles/pivots/pattern/targets | Frontend canvas does not draw real overlay yet |

## Line-By-Line Safety Audit

| Safety Rule | Status | Reason |
| --- | --- | --- |
| No pattern-only READY | PASS | Harmonic advanced output still returns WAIT/REJECT style states unless gates pass |
| Missing source must not crash app | PASS | openchart returns controlled FAIL payload |
| Unofficial data labelled | PASS | yfinance candles carry `UNOFFICIAL_TEMP` |
| Parquet failure must not break OHLCV fetch | PASS | fetch endpoint returns warning if Parquet save fails |
| Missing smart-money/OI must not be hidden | PASS | G12/G13 return `UNKNOWN` |
| Liquidity weakness must be visible | PASS | endpoint returns `SKIP_LIQUIDITY_WEAK` or PASS with unknown fields |
| 4H custom must not pretend full global 4H | PASS | second bar warning is generated as partial session |

## Not Perfect Yet

These are the remaining real gaps:

1. Superseded 2026-07-08: `nselib` is installed and verified; `openchart` is installed but not usable and remains fail-closed.
2. NSE holiday/calendar feed is not wired.
3. Market cap and ASM/GSM checks are not wired.
4. Smart-money, OI/MWPL/basis, sector, and momentum gates are named but not fully live.
5. Full all-NSE background scanner is not built.
6. Frontend does not yet render the real XABCD/PRZ/target overlay visually.
7. Pattern lifecycle does not yet update continuously after initial detection.

## Final Audit Result

```text
Local guarded prototype: PASS
Requested functions available: MOSTLY PASS
External-source-dependent functions: GUARDED, NOT LIVE
Full production screener: NOT YET
Claim of perfect/no-error/no-delay: NOT HONEST
Current response correctness: PASS for tested endpoints
```

## Double Verification - 14 Required Systems

| # | System | Current Status | Connected / Working Evidence | Gap |
| ---: | --- | --- | --- | --- |
| 1 | Licensed/live NSE intraday OHLCV feed | NOT BUILT | yfinance temporary adapter works and is labelled `UNOFFICIAL_TEMP` | Needs broker/licensed feed |
| 2 | NSE/BSE/AMFI/SEBI source parsers | PARTIAL FOUNDATION | Source catalog + freshness monitor has official links and snapshot checks | Real parsers for each report still pending |
| 3 | MCX data adapters | PLAN + SOURCE CATALOG | MCX bhavcopy source exists in catalog and MCX plan | Actual MCX parser not built |
| 4 | Real harmonic pattern detector | BUILT GUARDED | pyharmonics attempt + internal validator + advanced ratio engine | More known-pattern fixtures needed |
| 5 | Real OI/MWPL/futures basis/IV adapters | NOT BUILT | G13 gate exists and remains `UNKNOWN` | Needs official derivatives adapters and option data |
| 6 | Background scanner scheduler | PARTIAL | Source freshness scheduler built and verified | All-universe market scanner scheduler not built |
| 7 | Historical candle storage | BUILT | SQLite + Parquet verified | Retention/partition policy still basic |
| 8 | Outcome labelling for ML | PARTIAL | `outcome_label` column exists in ML candidates | No automated outcome updater yet |
| 9 | Feature engineering pipeline | NOT BUILT | Harmonic/gate fields stored as candidate payloads | No dedicated feature table/export yet |
| 10 | Backtest validation | PARTIAL | Harmonic benchmark endpoint exists | Full backtest engine not built |
| 11 | User settings/account risk config | NOT BUILT | Mock risk rows only | Needs settings table/API/UI |
| 12 | Authentication if exposed outside local machine | NOT BUILT | Local-only app, permissive CORS | Must add auth before non-local exposure |
| 13 | Export/import tools | PARTIAL | Parquet write/read exists | ML dataset export/import not built |
| 14 | Production logging and monitoring | NOT BUILT | Tests and local status endpoints only | Needs structured logs, rotation, metrics, alerts |

## Source Freshness Monitor Verification

Built and verified:

```text
GET  /api/source-monitor/catalog
POST /api/source-monitor/check
GET  /api/source-monitor/history
GET  /api/source-monitor/scheduler/status
POST /api/source-monitor/scheduler/run-once
POST /api/source-monitor/scheduler/start
POST /api/source-monitor/scheduler/stop
```

Live evidence:

```text
Catalog source count: 23
CFTC COT fetch: HTTP 200, raw snapshot saved, hash saved, Last-Modified saved
CFTC dynamic-page false-change fix: PASS, stable Last-Modified + stable length now returns UNCHANGED
Scheduler start/status/stop: PASS
Backend tests: 21/21 PASS
Frontend checks: 57/57 PASS
```

Design reason:

Source pages can change raw HTML because of tokens, banners, timestamps, or tracking scripts. A raw hash-only system would create false `CHANGED` events and could make the scanner believe new data arrived when only the page chrome changed. The monitor now uses raw hash plus Last-Modified/content-length/ETag logic to reduce false freshness signals.

## Follow-Up Implementation - 2026-07-08

Built after rechecking the user's remaining missing list:

```text
Source parser result layer: BUILT
Gate readiness endpoint: BUILT
nselib dependency: INSTALLED and verified
openchart dependency: INSTALLED but not usable; remains fail-closed
```

New endpoints:

```text
POST /api/source-parser/run
GET  /api/source-parser/results
GET  /api/gates/readiness
```

Live verification:

```text
nselib import: PASS, version 2.5.1
nselib smoke test: PASS, RELIANCE 1d returned 255 candles
openchart import: PASS, version 0.2.0
openchart smoke test: FAIL CLOSED, RELIANCE returned no usable candles
CFTC parser: PARSED_METADATA_ONLY, 84 report/data links, dataDate from Last-Modified
Gate readiness: G12/G13/MCX_CONTEXT return DO_NOT_PASS_READY until structured source parsers exist
Backend tests: 24/24 PASS
Frontend checks: 55/55 PASS
```

Important correction:

`nselib` is no longer "install needed." It is installed and the daily EOD adapter now handles `OpenPrice`, `HighPrice`, `LowPrice`, `ClosePrice`, `TotalTradedQuantity`, and comma-formatted prices.

`openchart` is installed but not verified as usable. Its package API exists (`NSEData.historical`), but RELIANCE returned no usable candle data in this environment. Therefore the scanner must not rely on openchart yet.

Gate status after this slice:

| Gate | Previous | Current | Trading Effect |
| --- | --- | --- | --- |
| G12 Smart Money | UNKNOWN | Connected to source/parser readiness | Still blocks READY |
| G13 OI Confirms | UNKNOWN | Connected to source/parser readiness | Still blocks READY |
| MCX Context | Not connected | Connected to MCX/CFTC/WGC parser readiness | Still blocks READY |

## External AI Plan Comparison Audit - 2026-07-08

Three new attachment plans were read and compared against the current TrendForge plan/build.

### Accepted Into Master Plan

| Item | Status | Reason |
| --- | --- | --- |
| Internal data-date freshness | ADDED TO PLAN | HTTP headers prove fetch freshness, not report freshness |
| Shared structured parser contract | ADDED TO PLAN | Needed before official source gates can pass |
| New parser states | ADDED TO PLAN | Distinguishes metadata-only, empty parse, stale data, parse error |
| CFTC COT structured parser | ADDED TO PLAN | Stable official download data; good first parser-contract proof |
| NSE MWPL/F&O ban parser | ADDED TO PLAN | Highest-value NSE safety parser before OI interpretation |
| NSE participant OI parser | ADDED TO PLAN | Useful as aggregate regime context, not stock-level proof |
| NSE large/bulk/block parser | ADDED TO PLAN | Stock-specific smart-money deal anchors |
| AMFI monthly portfolio parser | ADDED TO PLAN | Official DII stock-level swing sponsorship with lag |
| MCX bhavcopy parser | ADDED TO PLAN | Official commodity EOD price/volume/OI confirmation |
| Raw source archive table | ADDED TO PLAN | Needed for future audit, ML, and replay |
| scanner_runs/scanner_candidates | ADDED TO PLAN | Needed to save every WAIT/REJECT/READY decision for ML |
| Fail-closed scheduler | ADDED TO PLAN | Prevents READY when critical source state is broken |
| Failure-first tests | ADDED TO PLAN | Required before gates are allowed to pass |

### Corrected Or Rejected From Attachments

| Attachment idea | Decision | Reason |
| --- | --- | --- |
| Copy sample MWPL code directly | REJECTED | Contains `pd.compat.StringIO`, weak schema detection, and unsafe assumptions |
| Sample date parser `%d-%m-%m` | REJECTED | Wrong format for DD-MM-YYYY; should be `%d-%m-%Y` |
| Single MWPL threshold at 85% | UPGRADED | Plan requires 80/90/95 staged warnings and hard block near ban |
| Treat AMFI/CFTC as live signals | REJECTED | AMFI is monthly lag, CFTC is weekly delayed |
| Use TradingView/commercial scanners as backend | REJECTED | Reference/QA only; no legal stable all-NSE backend API |
| Use participant OI as stock-level FII proof | REJECTED | Participant OI is aggregate context |
| Use SLB as exact short interest | REJECTED | SLB is a borrow-pressure proxy only |
| Keep openchart as scanner source today | REJECTED | Installed but no usable RELIANCE candles; must remain fail-closed |

### New Audit Expectation

Future implementation is not complete until tests prove:

```text
no snapshot blocks READY.
metadata-only blocks READY.
empty structured parse blocks READY.
stale or null data_date blocks READY.
parse error blocks READY.
source 403/429/500 blocks READY.
yfinance-only and openchart-failed data cannot produce READY.
AMFI cannot trigger intraday READY.
participant OI cannot claim stock-level FII proof.
scanner saves WAIT/REJECT candidates for research and ML, not only READY candidates.
```

## Structured Parser Build Audit - 2026-07-08

The 10 delivered parser/integration/test attachments were reviewed and implemented as a safe first build slice.

### Built

| Parser | Current status | Safety scope |
| --- | --- | --- |
| NSE MWPL/F&O ban | BUILT as snapshot parser | G13 safety; 80/90/95 logic preserved |
| NSE participant OI | BUILT as snapshot parser | AGGREGATE_CONTEXT_ONLY; never stock-level FII proof |
| NSE large/bulk/block deals | BUILT as snapshot parser | STOCK_LEVEL_DEAL_ANCHOR |
| AMFI portfolio | BUILT as snapshot parser | SWING_CONFIRMATION_ONLY; never intraday trigger |
| CFTC COT | BUILT for direct COT files; HTML page remains metadata-only | COMMODITY_REGIME_ONLY; weekly delayed |
| MCX bhavcopy | BUILT as snapshot parser | MCX_EOD_CONFIRMATION; not live intraday |

### Attachment Code Not Copied Directly

| Issue found | Fix applied |
| --- | --- |
| Parsers fetched websites directly | Reworked to parse saved raw snapshots only |
| Parser state used `PARSED` | Normalized to `PARSED_STRUCTURED` for gate confirmation |
| Pasted tests used incompatible pytest/class APIs | Ported safety checks into existing unittest API test file |
| CFTC parser could confuse page metadata with position data | Direct COT file rows can be structured; HTML page snapshots remain `PARSED_METADATA_ONLY` |
| AMFI and participant OI could be misread as live proof | Scope labels added in parser output |

### New Verification

```text
Python compile: PASS
Backend tests: 28/28 PASS
Frontend static checks: 57/57 PASS
Live /api/health on 8001: PASS
Live /api/gates/readiness: DO_NOT_PASS_READY for missing/metadata-only current sources
```

### Still Missing After This Build Slice

```text
official direct download resolver per source.
raw_source_archive table.
source-specific row tables and insert helpers.
all-universe scanner scheduler.
frontend parser detail grid.
real broker/licensed intraday feed.
```

## Completion Slice Audit - 2026-07-08

User requested completion of the remaining parser infrastructure items.

### Moved From Missing To Built

| Item | New status | Files |
| --- | --- | --- |
| Direct official download resolvers per source | BUILT GUARDED | `backend/trendforge_api/source_resolver.py`, `source_monitor.py` |
| `raw_source_archive` table | BUILT | `backend/trendforge_api/storage.py` |
| Row-level parser tables | BUILT | `mwpl_snapshots`, `participant_oi_daily`, `bulk_block_deals`, `amfi_scheme_holdings`, `amfi_stock_deltas`, `cftc_cot_positions`, `mcx_bhavcopy_daily` |
| CFTC official headerless file parser | BUILT AND LIVE VERIFIED | `f_disagg.txt` parses Gold/Silver/Crude/Copper/NG-related rows into `cftc_cot_positions` |
| Scanner run/candidate persistence | BUILT | `scanner_runs`, `scanner_candidates` |
| All-universe scanner scheduler | BUILT FAIL-CLOSED | `backend/trendforge_api/scanner_scheduler.py` |
| Frontend parser drilldown grid | BUILT | `frontend/index.html`, `frontend/styles.css`, `frontend/app.js` |

### Important Qualification

```text
The scheduler exists and persists scanner runs, but it is not yet a broker-grade all-NSE live scanner.
Until licensed/live OHLCV, real OI/MWPL/basis/IV adapters, and official source gates pass, it downgrades candidates to WAIT_SOURCE_CONFIRMATION.
This is intentional. It prevents false READY output from incomplete source evidence.
```

### New Endpoints Verified By Tests

```text
GET  /api/source-resolver/candidates
GET  /api/raw-source-archive
GET  /api/source-parser/domain-rows
GET  /api/scanner/scheduler/status
POST /api/scanner/run-once
POST /api/scanner/scheduler/start
POST /api/scanner/scheduler/stop
GET  /api/scanner/runs
GET  /api/scanner/candidates
```

### Verification

```text
Python compile: PASS.
Backend tests: 30/30 PASS.
Frontend acceptance checks: 62/62 PASS.
JavaScript syntax check: PASS.
Live CFTC fetch/parse: PASS, raw archive state PARSED_STRUCTURED, row table populated.
```
<!-- HISTORICAL_SOURCE_END path=TREND_FORGE_LINE_BY_LINE_AUDIT_2026-07-07.md sha256=ced274be886ce7372ec06b25eb77f372349fa3dcf8fc3ec0d756c9d0dea398b9 -->

<!-- HISTORICAL_SOURCE_BEGIN path=TREND_FORGE_REQUIREMENT_IMPLEMENTATION_AUDIT_2026-07-08.md sha256=b76262a3a75a81f286eb79160b04740a259d558eb95c1ec331ad68db2757c77b lines=329 -->
# TrendForge Requirement Implementation Audit - 2026-07-08

Purpose: honest line-by-line coverage audit of the earlier pasted requirements against the current build.

Status meanings:

```text
IMPLEMENTED = code, storage/API/UI, and tests or live check exist.
PARTIAL = some foundation exists, but the full trading requirement is not complete.
PLANNED_ONLY = written into docs/plans, but no working adapter/engine yet.
MISSING = not present in runtime and not meaningfully wired.
MOCK_ONLY = visible in demo candidate data, not real scanner logic.
FAIL_CLOSED = present, but intentionally blocks READY until real data exists.
```

## 1. Direct User Request From This Turn

| Requirement | Current status | Evidence | Honest note |
| --- | --- | --- | --- |
| Direct official download resolvers per source | PARTIAL | `backend/trendforge_api/source_resolver.py` has resolver candidates for CFTC, NSE participant OI, NSE MWPL, NSE large deals, AMFI, MCX bhavcopy | Not yet built for every saved source such as BSE buyback/open offer, SEBI PIT/SAST, MSEI, RBI, MCA, WGC, FRED, EIA, OPEC, LME |
| `raw_source_archive` table | IMPLEMENTED | `storage.py` creates `raw_source_archive`; live DB has 1 CFTC raw archive row | Needs retention/dedupe policy beyond current insert/update |
| Row-level tables like `mwpl_snapshots`, `cftc_cot_positions` | IMPLEMENTED FOR FIRST 6 PARSERS | `mwpl_snapshots`, `participant_oi_daily`, `bulk_block_deals`, `amfi_scheme_holdings`, `amfi_stock_deltas`, `cftc_cot_positions`, `mcx_bhavcopy_daily` exist | Only CFTC has live official rows right now; others are parser-ready but have no live fetched rows in DB |
| All-universe scanner scheduler | PARTIAL / FAIL_CLOSED | `scanner_scheduler.py`, `scanner_runs`, `scanner_candidates`, `/api/scanner/run-once` | Scheduler exists, but candidate generation still uses prototype radar candidates until a real all-NSE universe/feed scanner is connected |
| Frontend parser drilldown grid | IMPLEMENTED | `frontend/index.html`, `frontend/app.js`, frontend test checks parser drilldown and scanner button | It previews parser/archive/domain rows; it is not yet a full parser debugger with raw-file viewer |

## 2. Current Database Evidence

Current table counts from `D:\TrendForge\data\trendforge_research.db`:

```text
raw_source_archive: 1
cftc_cot_positions: 11
scanner_runs: 1
scanner_candidates: 5
source_snapshots: 12
source_parse_results: 12
ohlcv_candles: 125
harmonic_alerts: 4
harmonic_patterns: 0
mwpl_snapshots: 0
participant_oi_daily: 0
bulk_block_deals: 0
amfi_scheme_holdings: 0
amfi_stock_deltas: 0
mcx_bhavcopy_daily: 0
```

Interpretation:

```text
CFTC official file was actually fetched, archived, parsed, and stored.
MWPL/participant OI/large deals/AMFI/MCX parser tables exist but do not yet contain live official rows.
The scanner run saved 5 candidates, but all are WAIT_SOURCE_CONFIRMATION because official gate evidence is incomplete.
```

## 3. Source Links And Parsers From Earlier Inputs

| Source/link group from earlier input | Saved in plan/docs | Runtime catalog | Direct resolver | Parser | Row table | Status |
| --- | --- | --- | --- | --- | --- | --- |
| NSE MWPL/F&O ban | Yes | Yes | Yes | Yes | Yes | PARTIAL: parser built, no live MWPL rows in DB |
| NSE participant-wise OI | Yes | Yes | Yes | Yes | Yes | PARTIAL: parser built, no live rows in DB; correctly scoped as aggregate/regime only |
| NSE large/bulk/block deals | Yes | Yes | Yes | Yes | Yes | PARTIAL: parser built, no live rows in DB |
| AMFI monthly portfolio disclosure | Yes | Yes | Yes | Yes | Yes | PARTIAL: parser built, no live rows; true month-over-month delta not built |
| AMFI scheme-wise disclosure | Yes | Yes | Yes | Yes | Yes | PARTIAL: parser path built through AMFI parser, no live rows |
| CFTC COT | Yes | Yes | Yes | Yes | Yes | IMPLEMENTED for official `f_disagg.txt`; 11 live rows stored |
| MCX bhavcopy | Yes | Yes | Yes | Yes | Yes | PARTIAL: parser built, no live MCX rows in DB |
| NSE SLB reports | Yes | Yes | No | No | No | PLANNED_ONLY |
| BSE buyback tender offer | Yes | Yes | No | No | No | PLANNED_ONLY |
| BSE takeover/open offer | Yes | Yes | No | No | No | PLANNED_ONLY |
| NSE daily buyback | Yes | Yes | No | No | No | PLANNED_ONLY |
| NSE corporate actions | Yes | Yes | No | No | No | PLANNED_ONLY |
| SEBI PIT/SAST/FPI pages | Yes | Yes | No | No | No | PLANNED_ONLY |
| MSEI FII/DII | Yes | Yes | No | No | No | PLANNED_ONLY |
| RBI FPI monitoring | Yes | Yes | No | No | No | PLANNED_ONLY |
| MCA master data/SBO/charges | Yes | Yes | No | No | No | PLANNED_ONLY |
| World Gold Council gold OI | Yes | Yes | No | No | No | PLANNED_ONLY |
| NiftyTrader MCX Gold OI | Yes in MCX plan | No runtime catalog | No | No | No | PLANNED_ONLY/reference only |
| NiftyTrader live MCX OI dashboard | Yes in MCX plan | No runtime catalog | No | No | No | PLANNED_ONLY/reference only |
| Barchart COT / cotpricecharts / Quandl | Yes in plan as visual/API references | No runtime catalog | No | No | No | Reference only, not runtime data |
| FRED real yields, DXY, USD/INR, SGE premium, LBMA, ETF flows | Yes in MCX plan | Mostly no runtime catalog | No | No | No | PLANNED_ONLY |
| EIA/API/OPEC/Baker Hughes/LME/SHFE/China PMI/USDA/IMD | Yes in MCX plan | No runtime catalog | No | No | No | PLANNED_ONLY |

## 4. Stock Screener Logic Audit

| Requirement from earlier plan | Runtime status | Evidence | Gap |
| --- | --- | --- | --- |
| Screen 0 command bar | PARTIAL / MOCK_ONLY | `frontend/index.html`, `/api/command-bar`, mock command bar | Not calculated from live regime/VIX/breadth/source gates |
| Global macro gate | MOCK_ONLY / PLANNED_ONLY | Mock radar/command data | No real US/Asia/GIFT/FII/DII/news adapter |
| Market regime, VIX, breadth | PLANNED_ONLY | Mentioned in docs/mock data | No real VIX/breadth/advance-decline computation |
| Sector gate / sector heatmap / RRG | PLANNED_ONLY | Docs only | No sector data adapter or ranking engine |
| Stock safety: liquidity | PARTIAL | Harmonic `liquidity_prefilter` exists | No official all-NSE market cap/value/spread/ASM/GSM/operator safety feed |
| Stock safety: MWPL/F&O ban | PARTIAL | MWPL parser/table exists | No live MWPL rows yet; no stock card live MWPL state from current data |
| ASM/GSM/operator flag | PLANNED_ONLY | Docs only | No parser or gate |
| Smart money: bulk/block deals | PARTIAL | NSE large deals parser/table exists | No live rows; no continuous deal-anchor monitor against live price |
| Smart money: AMFI holdings | PARTIAL | AMFI parser/table exists | No live rows; true monthly delta engine not implemented |
| Smart money: SEBI PIT/SAST/pledge | PLANNED_ONLY | Source catalog only | No parser/scorer |
| Smart money quality grading: open-market vs ESOP/transfer/pledge | PLANNED_ONLY | Master plan/docs only | No classifier in runtime |
| OI quadrant: price/OI long build-up etc. | MOCK_ONLY / PLANNED_ONLY | Mock candidate text; parser foundations | No live stock futures OI adapter and no systematic stock-card OI quadrant from official data |
| MWPL before OI interpretation | PARTIAL | Parser + gate readiness concept | Cannot pass until live MWPL data exists |
| Futures basis/cost of carry | PLANNED_ONLY | Docs/mock candidate text | No spot/futures basis adapter/table |
| Rollover interpretation near expiry | PLANNED_ONLY | Docs only | No near/far expiry OI roll parser |
| Options IV/OI confluence | PLANNED_ONLY | Docs only | No option chain, IV, IV rank, skew, Greeks, or PCR adapter |
| Greeks calculation | MISSING | No `py_vollib`, mibian, or Greeks module in runtime | Not built |
| Volume quality: RVOL/VWAP | PARTIAL | Harmonic detector computes volume ratio and VWAP | No trade count, average trade size, spread-adjusted volume, location by candle segment |
| SLB borrow proxy | PLANNED_ONLY | Source catalog only | No parser/table/gate |
| Participant-wise OI scope clarification | IMPLEMENTED | Parser scope is aggregate/regime only | Correctly does not claim stock-level FII proof |
| Conflict matrix / named output states | PARTIAL | WAIT/READY/REJECT states and fail-closed scanner downgrade exist | Full confluence truth table not implemented |
| Emotional safety gate | PARTIAL / MOCK_ONLY | Manual lock UI exists; mock safety states | No real P&L, recent-loss, revenge-trade, distress detector |
| FOMO lock after big gap | MOCK_ONLY / PLANNED_ONLY | Mock candidate reasons; harmonic risk concepts | No live ATR-vs-entry gate for stocks |
| Supply overhang tracking | MOCK_ONLY / PLANNED_ONLY | Mock HDFCBANK candidate; docs | No parser for seller remaining holdings and absorption tracking |
| Risk engine position sizing | MOCK_ONLY / PARTIAL | Mock candidates include risk fields | No user account/risk settings engine |
| Execution/post-entry monitor | MISSING | No broker/order module | Intentionally not built |

## 5. Harmonic Screener Audit

| Requirement | Runtime status | Evidence | Gap |
| --- | --- | --- | --- |
| Temporary yfinance OHLCV adapter | IMPLEMENTED | `ohlcv_adapter.py`, `/api/ohlcv/fetch`, tests | Unofficial temp only |
| Store candles | IMPLEMENTED | `ohlcv_candles`, `/api/ohlcv/candles` | Retention not implemented |
| Parquet candle store | IMPLEMENTED | `parquet_store.py`, `/api/parquet/*` | Used locally, not large-scale optimized |
| pyharmonics detector | PARTIAL | `attempt_pyharmonics` exists | pyharmonics result count is attempted; internal validator drives final card |
| Internal harmonic ratio validator | PARTIAL/IMPLEMENTED INITIAL | `validate_harmonic_ratios` | Needs more fixture coverage for complex edge cases |
| Gartley/Bat/Crab/Cypher/Shark/5-0 | PARTIAL | Ratio validator exists | Needs deeper known-pattern tests and visual QA |
| 30m/1h/4h/1d/1w timeframes | PARTIAL | UI supports them; yfinance/adapters support many | Real all-NSE intraday source missing |
| Exact NSE custom 4H builder | IMPLEMENTED | `/api/nse/4h-custom/build`, `nse_session.py` | Depends on valid intraday candles |
| openchart adapter | PARTIAL / FAIL_CLOSED | Adapter installed | Smoke failed earlier; not usable for production scan |
| nselib adapter | PARTIAL | Installed and EOD adapter exists | EOD only, not intraday all-NSE |
| Liquidity pre-filter | PARTIAL | `liquidity_prefilter` | Lacks official market cap/spread/ASM/GSM data |
| Multi-sensitivity ZigZag | IMPLEMENTED INITIAL | `build_multi_sensitivity_pivots` | Needs performance tests for all-universe scan |
| Pivot deduplication/quality | IMPLEMENTED INITIAL | `_dedupe_alternating`, pivot quality | Needs no-lookahead tests and more fixtures |
| Weighted hybrid quality score | IMPLEMENTED INITIAL | `hybrid_quality_score` | Weight tuning not validated |
| G00-G14 gates | PARTIAL | `score_gates` | G04/G05/G06/G10/G11/G12/G13 still return UNKNOWN/pending |
| Volume/VWAP confirmation | PARTIAL | G08/G09 exist | Based on available candle data only |
| Smart-money/OI gates for harmonic READY | FAIL_CLOSED | `harmonic_detector.py` returns `WAIT_DATA_MISSING` for smart money and OI/MWPL/basis | Correctly blocks unsafe confirmation |
| Pattern lifecycle | PARTIAL | `lifecycle_state`, alerts | No ongoing background lifecycle updater to WIN/LOSS outcomes |
| Alert center | PARTIAL | `harmonic_alerts`, `/api/harmonic/alerts` | UI is basic; no Telegram/email/Windows alerts |
| Chart overlay XABCD/PRZ/targets | PARTIAL | `/api/harmonic/chart-overlay` returns payload | Frontend canvas does not draw real overlay yet |
| ML snapshot saving | IMPLEMENTED INITIAL | `ml_scan_runs`, `ml_scan_candidates`, harmonic scan saves ML run | No real training pipeline |
| Outcome labelling | PARTIAL SCHEMA ONLY | `outcome_label` column exists | No endpoint/job to label WIN/LOSS after time passes |
| Backtest validation | PARTIAL | Single-symbol benchmark endpoint | No full backtest engine |

## 6. MCX Scanner Audit

| Requirement | Runtime status | Evidence | Gap |
| --- | --- | --- | --- |
| MCX plan and links saved | IMPLEMENTED IN DOCS | `TREND_FORGE_MCX_SCANNER_PLAN.md` | Not all links are runtime catalog entries |
| MCX bhavcopy parser | PARTIAL | Parser/table exists | No live MCX row currently in DB |
| CFTC COT parser for MCX context | IMPLEMENTED | Live CFTC `f_disagg.txt` parsed; 11 rows stored | Percentile/crowding over history not implemented |
| COMEX Gold + USD/INR translation | PLANNED_ONLY | MCX plan only | No live COMEX or USD/INR adapter |
| DXY and US real yields | PLANNED_ONLY | MCX plan only | No FRED/DXY adapter |
| Gold ETF flows, SGE premium, LBMA, imports | PLANNED_ONLY | MCX plan only | No parser |
| MCX-COMEX parity/premium | PLANNED_ONLY | Formula in plan | No calculator endpoint/table |
| MCX near/far basis | PLANNED_ONLY | Plan only | No near/far contract parser |
| MCX OI quadrant | MOCK_ONLY / PLANNED_ONLY | Mock MCX candidate text | No live MCX intraday OI adapter |
| EIA/API/OPEC crude framework | PLANNED_ONLY | MCX plan only | No event calendar/parser |
| LME/SHFE/China PMI base metals framework | PLANNED_ONLY | MCX plan only | No adapters |
| USDA/IMD/agri framework | PLANNED_ONLY | MCX plan only | No adapters |
| MCX options/IV/PCR | PLANNED_ONLY | MCX plan only | No option chain adapter |
| MCX command bar/session timing | MOCK_ONLY / PLANNED_ONLY | UI has MCX mode and mock candidate | No live session state engine |

## 7. Fourteen-Item Production Checklist

| Item | Current status | Reason |
| --- | --- | --- |
| 1. Licensed/live NSE intraday OHLCV data feed | NOT BUILT | yfinance/nselib/openchart are temporary/unofficial; no broker/licensed feed |
| 2. NSE/BSE/AMFI/SEBI source parsers | PARTIAL | First NSE/AMFI parsers built; BSE/SEBI/MSEI/RBI/MCA not built |
| 3. MCX data adapters | PARTIAL | MCX bhavcopy parser + CFTC context built; live MCX/COMEX/USDINR missing |
| 4. Real harmonic pattern detector | PARTIAL | Internal detector + pyharmonics attempt built; production validation incomplete |
| 5. Real OI/MWPL/futures basis/IV adapters | PARTIAL/MOSTLY NOT BUILT | MWPL parser only; OI/futures basis/IV/Greeks not live |
| 6. Background scanner scheduler | PARTIAL | Scheduler exists, but uses prototype candidates and fail-closed gates |
| 7. Historical candle storage | IMPLEMENTED INITIAL | SQLite + Parquet |
| 8. Outcome labelling for ML | PARTIAL SCHEMA ONLY | `outcome_label` exists but no labelling job/API |
| 9. Feature engineering pipeline | NOT BUILT | No ML feature pipeline module |
| 10. Backtest validation | PARTIAL | Benchmark endpoint only, not full point-in-time backtest |
| 11. User settings/account risk config | NOT BUILT | No persisted account/risk settings |
| 12. Authentication if exposed outside local machine | NOT BUILT | Local open API/CORS still permissive |
| 13. Export/import tools | NOT BUILT | No export/import endpoints |
| 14. Production logging and monitoring | NOT BUILT | No structured logging/monitoring stack |

## 8. What I Previously Overstated Or Missed

```text
1. "All source links saved and used" is not true.
   Many links are saved in markdown plans, but only a smaller set is in runtime source catalog, and only six have structured parsers.

2. "All-universe scanner scheduler" is only partially true.
   The scheduler exists, but it does not yet scan real Nifty50/Nifty200/Nifty500/F&O universe from live data.

3. "OI/MWPL/basis/IV gates built" is not true.
   MWPL parser exists. The rest are mostly planned or fail-closed placeholders.

4. "MCX scanner built" is not true.
   MCX plan, CFTC parser, and MCX bhavcopy parser exist. The full MCX decision engine does not.

5. "Smart money tracking built" is only partial.
   Large deals and AMFI parsers exist. SEBI PIT/SAST, pledge, buyback, open offer, supply overhang, and quality grading are not built.

6. "Harmonic scanner production ready" is not true.
   It is a guarded prototype with good foundations, but several gates are UNKNOWN and live all-NSE data is missing.

7. The runtime source catalog had stale labels.
   I corrected built parser labels in `source_monitor.py` during this audit.
```

## 9. Most Important Missing Work, In Build Order

```text
1. Add real source resolvers/parsers for NSE SLB, BSE buyback/open offer, SEBI PIT/SAST, NSE corporate actions, NSE daily buyback.
2. Add live or licensed all-NSE OHLCV/universe provider.
3. Add real stock futures OI, futures basis, rollover, option chain, IV, and Greeks adapters.
4. Connect MWPL + OI + basis + IV into stock-card gates instead of mock text.
5. Add AMFI true month-over-month holding delta with corporate-action adjustment.
6. Add smart-money quality grading: open-market buy vs ESOP/transfer/pledge/sale/discounted block.
7. Add SLB borrow-pressure parser and label it as squeeze proxy, not exact short interest.
8. Add source retention, parser re-run dedupe, and hash-based replay tests.
9. Add real all-universe scan loop using official/live data, not prototype candidates.
10. Add ML outcome labelling, feature engineering, and backtest validation.
11. Add user account/risk settings and real emotional safety based on P&L/recent losses.
12. Add authentication, restricted CORS, export/import, structured logs, and monitoring before any non-local exposure.
```

## 10. Verification Performed During This Audit

```text
Python compile: PASS
Backend tests: 30/30 PASS
Frontend acceptance checks: 62/62 PASS
JavaScript syntax check: PASS
Package import check:
- nselib 2.5.1 installed
- openchart 0.2.0 installed but previously fail-closed for usable candles
- pyharmonics installed
```

## 11. Source Contract And Gate Artifact Build - 2026-07-08

Built after reviewing the new safe-completion plan that required parser-output artifacts, source role handling, and gate decision persistence.

### Added

```text
backend/trendforge_api/source_contracts.py
```

New deterministic helpers:

```text
normalize_parser_status
freshness_status_for
parser_can_unlock_gate
source_state_blocks_ready
can_source_unlock_ready
```

New tables:

```text
source_parser_outputs
source_freshness_status
gate_decisions
source_replacement_map
```

New endpoints:

```text
GET /api/source-parser/outputs
GET /api/source-freshness-status
GET /api/gate-decisions
GET /api/source-replacement-map
```

Frontend update:

```text
Parser drilldown now shows normalized parser output status, freshness status, source role, and whether a source can unlock READY.
```

### Source Use Matrix Now Stored

The runtime database now stores safe roles for:

```text
openchart
yfinance
nselib
nsepython
TradingView harmonic scripts
commercial harmonic scanners
stock-pattern
AMFI monthly portfolio
NSE participant OI
NSE SLB
CFTC COT
secondary aggregators
SEBI PIT/SAST
MCA master data
RBI FPI monitoring
MCX bhavcopy
```

This implements the rule:

```text
REFERENCE_ONLY cannot unlock READY.
SECONDARY_DISCOVERY cannot unlock READY.
UNOFFICIAL_TEMP cannot unlock READY.
UNOFFICIAL_WRAPPER cannot unlock READY alone.
OFFICIAL_DELAYED_CONTEXT cannot prove live flow.
Only official/licensed structured fresh evidence can unlock gate truth, and even then it must match the symbol/market scope.
```

### What Still Remains

```text
Parser-output artifacts are saved, but not yet exported to Parquet.
Gate decisions are saved for scanner runs, but not yet attached per candidate row as explicit IDs.
Source roles are visible in the parser panel, but no full source-management admin grid exists.
The actual missing parsers/adapters from sections 3-7 remain pending.
```

### New Verification

```text
Python compile: PASS
Backend tests: 31/31 PASS
Frontend acceptance checks: 65/65 PASS
JavaScript syntax check: PASS
```
<!-- HISTORICAL_SOURCE_END path=TREND_FORGE_REQUIREMENT_IMPLEMENTATION_AUDIT_2026-07-08.md sha256=b76262a3a75a81f286eb79160b04740a259d558eb95c1ec331ad68db2757c77b -->

## 2026-07-11 Verified Source-First Integration Slice

The full `TrendForge_Source_Integration_Analysis.md` was audited against the
running repository. Accepted work is implemented in this order:

1. exact official F&O ban parsing with `FNO_BAN_ONLY` coverage;
2. symbol-level `BLOCKED_FNO_BAN` and full-G13 `WAIT_MWPL_PERCENTAGES`;
3. strict UDiFF required-column validation for price and OI calculations;
4. live immutable ingestion of NSE bulk deals and CFTC disaggregated COT;
5. CFTC publication-aware freshness;
6. removal of guessed MWPL and MCX artifact URLs that returned 404/HTML;
7. read-only OpenAlgo history and option-chain client using the documented POST contracts.

Unverified MWPL percentages, SLB direct downloads and MCX bhavcopy remain
fail-closed. Their next milestone starts only after a genuine artifact is
captured, hashed, schema-fixtured and proven through the source pipeline.

## 2026-07-13 Completed: Bounded Link Audit And Macro Normalization

Completed:

1. persistent run/row audit tables for the full 211-link manifest;
2. canonical duplicate detection and active source-contract mapping;
3. official direct-candidate resolution before landing-page fetch;
4. bounded fetch size, timeout, throttle and 25-ID run limit;
5. CSV/JSON/ZIP/HTML payload profiling and immutable raw archives;
6. FRED real-yield and broad-dollar source parsers, freshness and local rows;
7. audit APIs and complete failure-path tests.

Next batch priority remains AMFI current downloads, NSE SLB and official MCX
bhavcopy. Browser scraping is allowed only for candidate discovery and every
discovered artifact must be independently fetched and validated by TrendForge.
## 2026-07-13 AMFI Activation Progress

Completed:

- official scheme directory and quarter discovery;
- official per-fund API resolution with bounded concurrency;
- newest-populated-quarter fallback;
- explicit `Nil`/no-data handling and partial-coverage fail-close;
- response hashes, raw bundle archive and attempt ledger;
- quarterly exposure parser and lossless row persistence;
- freshness from quarter end and delayed-swing scope enforcement.

Next AMFI work:

1. Resolve and archive each AMC's monthly portfolio workbook.
2. Parse every applicable workbook sheet with AMC/scheme/period lineage.
3. Map ISIN to an effective-dated NSE instrument master.
4. Adjust monthly quantity changes for splits, bonuses, mergers and other
   corporate actions before classifying add/reduce/exit.
5. Keep scheme-wise quarterly exposure separate from monthly quantity truth.

## Institutional Engine Milestone - 2026-07-13

Completed:

1. Validated `config/config.yaml` for weights, thresholds, account risk, cache,
   approved hosts and all 37 submitted endpoint contracts.
2. Added async NSE session-aware fetches, per-host throttling, maximum response
   size, typed parameter validation, SQLite fetch ledger and SHA-256 raw files.
3. Added 35+ technical, volatility, volume and risk features with strict OHLCV
   validation and explicit missing values.
4. Added factor scoring, hard ASM/GSM/pledge/liquidity/event filters, separate
   anomaly veto, directional ensemble contract and stop-risk quantity sizing.
5. Added chronological walk-forward validation, report persistence and APIs for
   config, sources, models, features, analyze, batch screen, reports and tests.
6. Added the compact institutional frontend panel, Dockerfile, Makefile and
   optional pinned HMM/XGBoost research dependencies.

Required before production decisions:

1. Implement schema/data-date normalizers for the 20 raw-only contracts that do
   not already have a canonical parser owner.
2. Resolve or officially replace the nine broken and two wrong-content URL
   contracts without deleting their audit history.
3. Build point-in-time training datasets, fit and calibrate model artifacts,
   serialize versions/hashes and prove walk-forward thresholds out of sample.
4. Add an internal readiness resolver; never accept readiness from API clients.
5. Add licensed/OpenAlgo intraday input and synchronized USD/INR for MCX.
6. Run Nifty 50, then Nifty 200, then all-NSE performance and outcome tests
   before enabling an all-universe recurring institutional scan.


<!-- CONSOLIDATED_SOURCE_END label=IMPLEMENTATION_PLAN sha256=492855467DD054282F14F513EF7C0D26C156C224AEF28C59C7D3975286AC1918 -->

## NSE Market Activity Watch Integration - 2026-07-14

### Business Purpose

This slice creates an official NSE activity-discovery funnel for stocks showing
unusual participation. It does not predict a win and does not create a trade by
itself. It narrows the universe to symbols that deserve the normal TrendForge
price-structure, VWAP, sector, derivatives, liquidity, risk and safety checks.

### Connected Source Contracts

| Source key | Official endpoint | Normalized use |
| --- | --- | --- |
| `nse_volume_gainers` | `https://www.nseindia.com/api/live-analysis-volume-gainers` | One-week and two-week relative-volume change, LTP, price change and turnover |
| `nse_most_active_volume` | `https://www.nseindia.com/api/live-analysis-most-active-securities?index=volume` | Rank confirmation by traded volume |
| `nse_most_active_value` | `https://www.nseindia.com/api/live-analysis-most-active-securities?index=value` | Rank confirmation by traded value, which reduces low-price/high-share-count distortion |
| `nse_large_deals_snapshot` | `https://www.nseindia.com/api/snapshot-capital-market-largedeal` | Named bulk, block and short-deal context with quantity and WATP anchors |

The existing async HTTP client is used instead of adding the submitted
subprocess/curl script. This preserves the approved-host allowlist, browser-like
headers, best-effort NSE session seed, per-host throttling, timeout and response
size controls, SHA-256 immutable raw archive, fetch ledger and explicit stale
fallback. A homepage seed `403` is logged, but the public API request is still
attempted with the same session because all four verified APIs can return valid
JSON in that state.

The live snapshot endpoint is research activity context. It does not replace
the existing official bulk/block archive parser used for dated G12 evidence.

### Deterministic Ranking

Each symbol receives an `activity_score` from 0 to 100 using only observed
activity evidence:

1. up to 35 points for relative-volume expansion versus one-week/two-week
   averages;
2. 12 points for appearing in most-active-by-volume;
3. 16 points for appearing in most-active-by-value;
4. up to 10 points for current price-move magnitude;
5. 12 points for named large-deal evidence, plus up to 5 points for clear price
   acceptance above or below the weighted deal-price anchor.

Direction uses price sign plus acceptance versus the deal WATP. Short-deal
activity can strengthen a bearish interpretation only when price is also down.
The stored deal notional is gross observed activity, not net institutional flow.

Possible output states are limited to:

```text
WATCH_LONG
WATCH_SHORT
WAIT_CONFIRMATION
WAIT_PARTIAL_SOURCE
WAIT_STALE
```

The score meaning is permanently labelled
`EVIDENCE_STRENGTH_NOT_WIN_PROBABILITY`. `can_unlock_ready` is always `false`
for this layer.

### Required Trade Confirmations

Before an activity candidate can progress through the main scanner, all
applicable evidence must still pass:

1. fresh price acceptance above/below VWAP with ORB or market-structure
   confirmation;
2. aligned market and sector breadth;
3. tradable spread, depth and position-size capacity;
4. OI, MWPL and futures-basis confirmation for F&O symbols;
5. deterministic account-risk and emotional-safety gates.

Large volume without value rank may be low-price churn. A named deal without
post-deal acceptance may be distribution. A volume spurt against sector/market
breadth remains WAIT. Empty holiday/weekend data remains visible as no-data or
stale evidence and cannot inherit the prior session as fresh.

### API, Storage And Frontend

```text
POST /api/market-activity/fetch?limit=20
GET  /api/market-activity/latest?limit=8

SQLite tables:
  institutional_endpoint_fetches
  market_activity_runs
  market_activity_candidates

Raw archive:
  data/raw_sources/institutional_endpoints/<source_key>/<UTC-date>/<sha256>.json
```

The single-screen Institutional Factor Engine now contains an `Activity Watch`
list with refresh, source completeness, fetch timestamp, state, evidence score,
price move, relative-volume/rank facts and the first reason. Clicking a row only
selects an existing radar symbol or preloads the harmonic symbol input; it never
creates a synthetic radar candidate or executable order.

### Live Verification Evidence

Verified on 2026-07-14 against the running local build:

```text
nse_volume_gainers          RAW_ARCHIVED   25 rows
nse_most_active_volume      RAW_ARCHIVED   20 rows
nse_most_active_value       RAW_ARCHIVED   20 rows
nse_large_deals_snapshot    RAW_ARCHIVED  289 rows
  bulk 179 + block 24 + short 86

source completeness         100%
snapshot state              RESEARCH_ONLY
can_unlock_ready            false
saved candidates            20
WATCH_LONG / WATCH_SHORT    0 / 0 in this after-market snapshot
WAIT candidates             20
```

No symbol was promoted merely to make the panel look active. The observed rows
did not meet the deterministic activity-watch threshold with directional
confluence, so they correctly stayed `WAIT_CONFIRMATION`.

Verification results:

```text
Focused backend tests       24/24 PASS
Python compilation          PASS
JavaScript syntax           PASS
Frontend acceptance         115/115 PASS
Live API health             PASS on http://127.0.0.1:8001/
Live latest snapshot API    PASS
Raw SHA-256 archive         PASS for all four sources
SQLite run/candidate save   PASS
```

### Next Reliability Improvements

1. Attach sector and index breadth to each activity row before increasing its
   priority.
2. Reconcile buyer/seller legs by deal identity so net/gross quantities are
   separately reported without double interpretation.
3. Join F&O symbols to fresh MWPL, OI quadrant and basis evidence.
4. Store later MFE, MAE, target, stop and outcome labels for every WATCH and
   WAIT row, then calibrate a genuine out-of-sample probability model.
5. Add scheduled market-session refresh only after rate-limit, holiday,
   correction and duplicate-content tests pass.

## Current 215-Link Reconciliation - 2026-07-15 After Priority Adapter Normalization

The four Activity Watch contracts are now appended to the canonical inventory
as IDs 212-215. Its current verified
classification is:

```text
CONNECTED_FRESH_STRUCTURED       45
NOT_CURRENTLY_USABLE            170
TOTAL                            215
```

The four Activity Watch APIs added on 2026-07-14 are now inventory rows:

```text
ID 212  nse_volume_gainers                 25 rows
ID 213  nse_most_active_volume             20 rows
ID 214  nse_most_active_value              20 rows
ID 215  nse_large_deals_snapshot          289 rows
```

The canonical count is now:

```text
Inventory usable       45 of 215
Inventory non-usable  170 of 215
```

The 170 non-usable inventory rows are not all network failures. Their exact
classification is:

```text
METADATA_ONLY                       44
REFERENCE_ONLY                      24
HTML_SCHEMA_PENDING                 21
SECONDARY_DISCOVERY                 20
DUPLICATE_NO_NEW_CONTRACT           10
CONNECTED_EMPTY_NO_SIGNAL           10
ARTIFACT_CAPTURED_SCHEMA_PENDING     7
FETCH_BLOCKED                        8
DOCUMENT_ONLY                        8
REGISTERED_NO_OUTPUT                 5
OPEN_SOURCE_REFERENCE                5
LOCAL_OPERATION_ONLY                 3
CONNECTED_METADATA_ONLY              2
CONNECTED_STALE_STRUCTURED           2
RESOLVER_PENDING                     1
TOTAL                               170
```

Only eight are classified as actual `FETCH_BLOCKED` official URLs: DES
agriculture, IMD hydromet, OPEC MOMR, NSE encumbrance, two NSE Regulation 30
annual URLs, SEBI home and SEBI FPI statistics. Ten more are connected but
currently contain no dated signal; they remain visible as valid empty evidence
and are not rejected.

The complete row-by-row non-usable report, including every URL, purpose,
failure/restriction, safe use, parser/freshness state and next action, is below.
Its legacy filename is retained for compatibility, but it now contains 170 rows:

```text
D:\TrendForge\data\reports\NON_USABLE_187_LINKS_2026-07-14.csv
```

The canonical full inventory remains one CSV. Its legacy filename is retained
to avoid breaking existing references, but it now contains 215 rows:

```text
D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-14.csv
```

The former 29-row `connected but currently unusable` assistance batch has been
reconciled without dropping any row. It now contains 14
`CONNECTED_FRESH_STRUCTURED`, two `CONNECTED_STALE_STRUCTURED`, one
`CONNECTED_EMPTY_NO_SIGNAL`, three `DUPLICATE_NO_NEW_CONTRACT`, two
`CONNECTED_METADATA_ONLY`, and seven `ARTIFACT_CAPTURED_SCHEMA_PENDING` rows.
All 29 URLs and their current purpose,
evidence, reason, safe use and next implementation action remain exported at:

```text
D:\TrendForge\data\reports\CONNECTED_BUT_UNUSABLE_29_LINKS_2026-07-14.csv
```

## Verified Disclosure Intelligence Normalization - 2026-07-14

### Attachment decision

The external `Stock Scanner - Data Ingestion Guide (29 Sources)` was reviewed
against current TrendForge endpoint contracts and archived live payloads. It is
useful for source roles, cadence, session reuse, deduplication, raw archiving,
cross-exchange confirmation and symbol mapping. Its standalone `requests` +
SQLite scraper was not copied because TrendForge already has a typed async
`httpx` client, host allowlist, exchange seeding, rate limiting, retries,
immutable SHA-256 raw archives and a shared research database.

Endpoint guesses marked `[VERIFY]` were not accepted as source truth. In
particular, the guide's `BlockDeal/w`, `BulkDeal/w`, `SastReg29/w`,
`SastPledgeMore/w`, `corporate-sast-reg29`, `corporate-pledgedata` and
`backpage.aspx/GetOptionChain` examples do not replace TrendForge's locally
verified contracts. The exact NSE pledge contract remains case-sensitive:

```text
https://www.nseindia.com/api/corporate-pledgeData
```

### Implemented source-specific normalizers

The following 13 existing endpoint contracts now normalize automatically after
the corporate or extended-market batch fetch completes:

```text
nse_announcements
nse_shareholding_pattern
nse_pledge
nse_regulation_31
nse_pit
nse_regulation_29
nse_tender_buyback
bse_corporate_announcements
bse_insider_trading
bse_pledge_data
bse_sast
bse_bulk_deals
bse_block_deals
```

The normalized event contract preserves fields that the old generic corporate
event model would lose:

```text
source key and source content hash
event-level SHA-256 identity
source record ID
NSE symbol / BSE scrip code / ISIN / company
event type, category and buy/sell/create/release/invoke side
actor and counterparty
event date and publication timestamp
quantity, price and notional
holding percentage before/change/after
promoter holding percentage
pledged shares, pledge percentage of promoter holding and total shares
headline, attachment URL and revision status
the complete original source row
```

Fresh empty responses are stored as `VALID_EMPTY`, not failures. Stale cached
responses become `STALE_FALLBACK`. Wrong shapes become `SCHEMA_MISMATCH`.
Fetch failures become `FETCH_FAILED`. None of these events can independently
unlock `READY`; all normalized output remains `RESEARCH_ONLY` and requires
price acceptance, freshness, market/sector, derivatives when applicable, risk
and safety confirmation.

### Immutable lineage storage

Four additive SQLite tables were created in
`D:\TrendForge\data\trendforge_research.db`:

```text
institutional_disclosure_runs
institutional_disclosure_sources
institutional_disclosure_events
institutional_disclosure_run_events
```

An identical event row is stored once by its event-level SHA-256 identity and
linked to every normalization run that observed it. A corrected/revised row
creates a new event identity; earlier evidence is not overwritten. Every source
status also retains the raw response content hash so a normalized decision can
be traced back to the immutable archive.

### API and runtime evidence

New read-only drilldown route:

```text
GET /api/institutional/disclosures/latest?symbol=RELIANCE&limit=100
```

The existing batch routes keep their response contracts and now persist a
normalization run after fetching:

```text
POST /api/institutional/corporate-sources/fetch
POST /api/institutional/extended-market-sources/fetch
```

Real archived payload backfill result on 2026-07-14:

```text
run_id: 59c774cb-a4e9-42a8-9145-b625988b6326
state: RESEARCH_ONLY
source contracts: 13
normalized events: 3,567
rejected rows: 0
can_unlock_ready: false
```

Source normalization totals from the verified archive:

```text
nse_announcements             20 STRUCTURED_OK
nse_shareholding_pattern      90 STRUCTURED_OK
nse_pledge                  1532 STRUCTURED_OK
nse_regulation_31             83 STRUCTURED_OK
nse_pit                        0 VALID_EMPTY
nse_regulation_29             45 STRUCTURED_OK
nse_tender_buyback             0 VALID_EMPTY
bse_corporate_announcements    5 STRUCTURED_OK
bse_insider_trading            0 VALID_EMPTY
bse_pledge_data             1242 STRUCTURED_OK
bse_sast                      37 STRUCTURED_OK
bse_bulk_deals               513 STRUCTURED_OK
bse_block_deals                0 VALID_EMPTY
```

BSE bulk deals use `P` for purchase in the captured response. The parser maps
`P` and `B` to `BUY`, and `S` to `SELL`. This was found by the real archive
backfill after an initial 239-row partial rejection; after correction all 513
rows normalize and zero rows are rejected.

### Verification

```text
python -m py_compile backend/trendforge_api/disclosure_intelligence.py backend/trendforge_api/main.py
$env:PYTHONPATH='backend'; python -m pytest backend/tests -q
Result: 291 passed

Live server: http://127.0.0.1:8001/
Health: ok
Latest disclosure API: RESEARCH_ONLY, 13 sources, 3,567 events
RELIANCE filter: only RELIANCE symbol records returned
```

Mocked API tests now replace disclosure persistence with a no-op. This prevents
test runs from writing empty fake runs into the real research database. The
runtime database was restored from the latest archived source payloads after
the test-isolation fix.

### Guidance deferred or rejected

```text
Standalone synchronous requests scraper
  Rejected: duplicates the safer async source client and lineage store.

Unverified NSE/BSE/MCX endpoint guesses
  Rejected: locally verified endpoint contracts remain authoritative.

DevTools endpoint discovery as automatic self-healing
  Rejected for runtime: useful for manual repair only; contract changes require
  schema fixtures, parser-version review and deterministic tests.

Broad except/pass and print-based infinite polling loop
  Rejected: hides failures, lacks structured logs, locks and market calendar.

EIA v2 petroleum/natural-gas series
  Deferred: technically useful, but requires an EIA API key and separate
  commodity-context schemas. It must not enter corporate-event storage.

USDA WASDE/PSD and Cornell ESMIS
  Deferred: useful for agricultural context; direct file/API contracts and
  credentials must be verified before implementation.

CDSL FPI and DGCI&S form automation
  Deferred: require stable dated artifact discovery and schema fixtures.

SGE, CFTC, Baker Hughes and MCX context
  Kept in their existing dedicated source/parser families. They are not forced
  into disclosure event schemas because their cadence and trading meaning differ.
```

## Source Connection Reconciliation - 2026-07-15

The row-level authority remains
`D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-14.csv`.
The compatibility filename is unchanged, but the file contains 215 unique URLs
with `status_as_of=2026-07-14`.

```text
Fresh structured and currently usable: 45
Not currently usable: 170
Total canonical inventory: 215

Of the 170 non-usable rows, only 8 are FETCH_BLOCKED. The others are:
metadata-only 44; reference-only 24; HTML schema pending 21;
secondary discovery 20; duplicate/covered 10; valid empty/no signal 10;
artifact captured/schema pending 7; document-only 8; registered/no output 5;
open-source reference 5; local operation only 3; connected metadata-only 2;
resolver pending 1; connected stale structured 2.
```

Highest-priority unique non-usable inventory IDs, revised after removing source
families already covered by a connected canonical contract:

```text
56  AMFI monthly portfolio disclosure
81  BSE buyback tender offers
82  BSE takeover/open offers
72  BSE shareholding pattern
137 NSE insider trading plans
144 NSE Regulation 30 annual archive
168 NSE exchange market-surveillance actions
171 NSE tender-offer/buyback reports
83  BSE corporate actions for BSE-only and cross-exchange reconciliation
113 MCX option-chain fresh-session repair
115 MCX delivery reports
117 MCX participant/member/MWPL disclosures
51  LME warehouse stocks
41  OPEC monthly oil market report
94  EIA natural-gas data
10  Baker Hughes fresh-download/revision repair
54  USDA WASDE supply/demand report
27  DGCI&S Indian import/export statistics
30  IMD hydrometeorological and rainfall data
52  SHFE inventory, price and report context
```

Separate NSE Regulation 7/29 pages, NSE encumbrance, BSE SAST/pledge variants,
bulk/block variants and duplicate SEBI documents are intentionally excluded from
this top 20 because current NSE PIT, Regulation 29, Regulation 31, pledged-data,
BSE SAST, BSE pledge and large-deal contracts already cover those evidence
families. They require contract consolidation or historical enrichment, not a
new independent gate source.

The following earlier ranks are retained as the next candidate pool. Items that
now appear in the top 20 above must not be counted twice:

```text
21  ID 54  USDA WASDE supply/demand report
22  ID 27  DGCI&S Indian import/export statistics
23  ID 30  IMD hydrometeorological and rainfall data
24  ID 28  Directorate of Economics and Statistics agriculture data
25  ID 52  SHFE inventory, price and report context
26  ID 53  China NBS economic and industrial releases
27  ID 116 MCX surveillance future-prices reports
28  ID 118 MCX trading-holiday and session calendar
29  ID 110 MCX circulars and contract-rule changes
30  ID 19  FBIL reference rates and financial benchmarks
31  ID 74  BSE XBRL filing detail resolver
32  ID 162 NSE XBRL taxonomy and filing-format resolver
33  ID 139 NSE annual PIT/insider archive
34  ID 152 NSE system-driven shareholding-pattern archive
35  ID 109 MCA master data, charges and ownership context
36  ID 87  CDSL foreign portfolio investor reports
37  ID 174 RBI FPI monitoring and ownership-limit context
38  ID 93  CFTC COT release schedule
39  ID 98  EIA weekly petroleum release schedule
40  ID 124 MSEI FII/DII activity
```

Ranks 21-26 are primarily sector or commodity catalysts; 27-30 protect session,
expiry, benchmark and contract interpretation; 31-37 enrich structured ownership,
insider and corporate lineage; 38-40 improve release-timing and aggregate-flow
context. None can independently create READY.

These sources remain fail-closed. Empty, stale, metadata-only, schema-pending,
blocked or unfetched rows cannot unlock READY and must not be converted to zero
or inferred evidence.

## Priority Source Adapter Completion - 2026-07-15

The canonical inventory expanded from 211 to 215 unique URLs when four NSE
market-activity contracts were explicitly added. The exact current classification
is maintained in `TREND_FORGE_SOURCE_REGISTRY.md` and
`data/reports/CURRENT_211_LINK_USABILITY_2026-07-14.csv`.

```text
CONNECTED_FRESH_STRUCTURED       45
CONNECTED_STALE_STRUCTURED        2
all other non-fresh states      168
total canonical URLs            215
```

Implemented in this change:

- current NSE and BSE UDiFF EOD resolvers with strict content/schema parsing;
- corrected AMFI position deltas keyed by AMC, scheme, ISIN and stock;
- MCX option-chain row normalization and research-only PCR, OI walls and
  writer-payout max-pain calculations;
- SGE benchmark normalization without inventing an LBMA premium;
- Baker Hughes workbook normalization for delayed crude supply context;
- immutable source-hash lineage and SQLite commodity context snapshots;
- `GET /api/institutional/commodity-context/latest`;
- a compact frontend MCX context panel showing date, freshness/state and
  limitations.

Observed bounded data:

```text
NSE EOD UDiFF                 2,382 rows, 2026-07-15
BSE EOD UDiFF                 4,857 rows, 2026-07-15
FRED broad dollar             5,144 observations, latest 2026-07-10
AMFI scheme-wise                460 rows, quarter end 2026-03-31
MCX option chain                332 normalized rows, stale 2026-07-14
SGE benchmark                 4,974 observations, latest 2026-07-13
Baker Hughes NA rigs            760 total, report date 2026-07-10
```

Screener interpretation loop:

```text
fetch -> archive/hash -> source-specific schema -> source date/freshness
-> normalized rows -> scope-specific context -> conflict checks
-> setup and normal gates -> deterministic risk -> WAIT/REJECT/READY
```

For stocks, NSE/BSE EOD provides price/volume structure, AMFI provides delayed
swing sponsorship context, and FRED provides macro regime context. For MCX,
option OI metrics, SGE trend and rig counts are context inputs only. They must be
combined with fresh official MCX price/OI, global benchmark, USD/INR, liquidity,
event and risk evidence before READY is possible.

Not accepted as complete integrations:

- guessed BSE/MCX routes that returned branded HTML or 404 responses;
- AMFI monthly portfolio HTML without resolved stock-holding rows;
- SGE/LBMA premium without synchronized LBMA, FX, tax, unit and timestamp data;
- Greeks or GEX from option rows lacking validated IV, lot size and signed dealer
  positioning;
- OPEC, LME and keyed EIA sources without a verified official artifact contract.

Remaining priority work is a stable AMFI monthly holdings workbook resolver, a
fresh MCX session contract, Baker Hughes retry/revision handling, verified
LME/OPEC/EIA resolvers, and the complete MCX global stack. Unofficial fallbacks
may support research but cannot unlock execution.



---

## 2026-07-16 Link Usability Reconciliation After Scanner Parser Build

The 13-source NSE/BSE scanner parser fetcher was live-tested and saved to:

`D:\TrendForge\data\reports\scanner_parser_fetch_verify_2026-07-16.json`

Current reconciled inventory count is now:

```text
Fresh structured usable links: 47
Not fresh structured links:    186
Connected but limited links:   26
Inventory rows tracked:        233
Previous fresh count:          45
Net increase:                  +2
```

The increase came from BSE block-deal links that now returned and normalized 46 structured rows. The latest 13-source run itself produced 8 fresh structured sources, 4 valid empty sources, 1 stale fallback source, 0 broken sources, and 3176 normalized disclosure events.

Updated files:

- `D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-16.csv`
- `D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-16.xlsx`
- `D:\TrendForge\data\reports\NON_USABLE_186_LINKS_2026-07-16.csv`
- `D:\TrendForge\data\reports\CONNECTED_BUT_UNUSABLE_26_LINKS_2026-07-16.csv`
- `D:\TrendForge\data\reports\LINK_USABILITY_SUMMARY_2026-07-16.md`


---

## 2026-07-16 Duplicate Link Audit

A duplicate/same-data audit was run against `D:\TrendForge\data\reports\CURRENT_211_LINK_USABILITY_2026-07-16.csv`.

```text
Inventory rows:                         233
Unique normalized URLs:                 217
Normalized URL duplicate groups:         16
Extra rows from URL duplicates:          16
Resolved endpoint duplicate groups:       6
Extra rows from resolved duplicates:      6
Unique active data contracts:            68
Same active data contract groups:        14
Extra rows from same data contracts:     17
Rows involved in any duplicate group:    58
```

Detailed files:

- `D:\TrendForge\data\reports\DUPLICATE_LINK_AUDIT_2026-07-16.md`
- `D:\TrendForge\data\reports\DUPLICATE_LINK_AUDIT_2026-07-16.csv`
- `D:\TrendForge\data\reports\DUPLICATE_LINK_AUDIT_2026-07-16.xlsx`

Operational rule: keep one canonical row per active data contract for automated fetching, and keep duplicate landing/manual/reference rows only as mirrors or documentation.


---

## 2026-07-17 NSE Index Derivative Route Merge

The pasted `nse_client.py` guide was checked against live NSE responses and merged only where it improved working source contracts.

Accepted and connected:

```text
nse_live_equity_derivatives_index_opt       -> index=nse50_opt       -> RAW_ARCHIVED, 1464 rows
nse_live_equity_derivatives_index_fut       -> index=nse50_fut       -> RAW_ARCHIVED, 3 rows
nse_live_equity_derivatives_banknifty_opt   -> index=nifty_bank_opt  -> RAW_ARCHIVED, 993 rows
nse_live_equity_derivatives_banknifty_fut   -> index=nifty_bank_fut  -> RAW_ARCHIVED, 3 rows
```

Rejected from this pasted module:

```text
option-chain-indices   -> 404 from this machine
quote-slb              -> 403 from this machine
/api/slbs              -> 404 from this machine
index=cash/fno         -> JSON error payload: Missing index or key
```

Implementation:

- Updated `D:\TrendForge\config\config.yaml`.
- Updated `D:\TrendForge\backend\trendforge_api\institutional_sources.py`.
- Updated `D:\TrendForge\backend\trendforge_api\intraday_stock_details.py`.
- Updated tests in `D:\TrendForge\backend\tests`.
- Updated `D:\TrendForge\tmp_duplicate_audit\build_source_link_master.mjs`.
- Rebuilt `D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx`.

Screener use:

- These routes now feed `marketContext` with Nifty and Bank Nifty index option/future record count, volume, and open interest.
- They are regime/context evidence only and do not unlock READY by themselves.

Verification:

```text
python -m py_compile institutional_sources.py intraday_stock_details.py -> passed
pytest test_intraday_stock_details.py test_institutional_screener.py -q -> 21 passed
TrendForge live fetch report -> data/reports/archive/2026-07-17_link_report_cleanup/index_derivative_fetch_after_pasted_module_2026-07-17.json
```

Master workbook after rebuild:

```text
MASTER_CURRENT:                 366
LINKED_SOURCES:                 98
NOT_LINKED_SOURCES:             231
SUPPRESSED_NOT_LINKED_DUPES:     21
ALL_LINKS_FROM_REPORTS:         350
Missing from workbook:            0
Extra in workbook:                0
Linked/not-linked URL overlap:    0
Linked/not-linked source overlap: 0
```


---

## 2026-07-17 Successful 12-Route Screener Source Merge

The user-listed 12 successful routes were merged into the existing TrendForge source catalog and screener paths without adding duplicate standalone downloader files.

Connected and live-verified through `AsyncEndpointClient`:

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

Implementation:

- Added `nsdl_fpi_daily_reportdetail` to the intraday stock-detail source set.
- Added `nse_shareholding_pattern` to symbol-level intraday stock-detail requests.
- Added `cftc_legacy_futures_only`, `cftc_disagg_futures_only`, and `cftc_tff_futures_only` to macro-event source requests and CFTC regime context.
- Bounded CFTC SODA routes to latest-first `500` rows so they stay under TrendForge's 10 MB raw-response safety guard.
- Reused existing files:
  - `D:\TrendForge\config\config.yaml`
  - `D:\TrendForge\backend\trendforge_api\institutional_sources.py`
  - `D:\TrendForge\backend\trendforge_api\intraday_stock_details.py`
  - `D:\TrendForge\backend\trendforge_api\macro_event_context.py`
  - `D:\TrendForge\tmp_duplicate_audit\build_source_link_master.mjs`

Screener check:

- Snapshot report: `D:\TrendForge\data\reports\archive\2026-07-17_link_report_cleanup\successful_12_screener_snapshot_check_2026-07-17.json`
- Snapshot state: `RESEARCH_ONLY`.
- Sources in snapshot: 12.
- Fresh sources: 12.
- `nsdlFpiTableCount`: 17.
- RELIANCE candidate now includes promoter/public shareholding evidence dated `30-JUN-2026`.

Verification:

```text
python -m py_compile institutional_config.py institutional_sources.py intraday_stock_details.py macro_event_context.py -> passed
pytest test_intraday_stock_details.py test_macro_event_sources.py test_institutional_screener.py -q -> 27 passed
Live 12-route fetch -> 12 fresh RAW_ARCHIVED, 0 broken, 0 stale fallback, 0 wrong content
```

Master workbook after rebuild:

```text
MASTER_CURRENT:                 370
LINKED_SOURCES:                 105
NOT_LINKED_SOURCES:             231
SUPPRESSED_NOT_LINKED_DUPES:     18
ALL_LINKS_FROM_REPORTS:         354
Missing from workbook:            0
Extra in workbook:                0
Linked/not-linked URL overlap:    0
Linked/not-linked source overlap: 0
```
