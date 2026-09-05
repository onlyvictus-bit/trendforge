# TrendForge Inventory App — Project Index

## Current official-source extension (2026-08-11)

Current catalog: **165 rows / 129 logical keys**. Upstream TrendForge registry:
**123 contracts**. New populated cards are BSE financial-results filing index
5,126 rows, BSE shareholding filing index 5,508 rows, and RBI T-bill auction
yields 3 rows. Internal calculated objects are not counted as links: industry
peers 500, option Greeks 65 and one prospective PCR/Max-Pain observation.
`fundamental_ratios_v1` remains empty until numeric iXBRL facts are available.
All are research-only and zero-score; panel formulas are unchanged.

## Files 1-7 recovery checkpoint (historical, 2026-08-11)

That recovery checkpoint used **158 rows / 122 logical keys** and registry
**116 contracts**. Exact status for all 77 supplied routes:
`D:\TrendForge\docs\fable\evidence\FREE_SOURCE_RECOVERY_77_MATRIX_20260811.csv`.
Anonymous replacements with real rows are exported now; 15 free read-only
Upstox contracts wait for a user Analytics token and are not falsely shown as
populated. ATM-IV rank waits for 252 observed sessions. All recovery fields are
informational and zero-score.

## Packs 6-7 verification (historical checkpoint, 2026-08-11)

TrendForge's existing NSE option-chain paths were repaired, live-persisted and
regression-tested. Pack 7's login/credential routes remain explicitly blocked;
synthetic data routes are rejected. No duplicate source card, browser fetcher,
Consensus voter or Screener score term was added.

## Pack 5 additions (2026-08-11)

Cards now include official NSE market-session status, repaired per-symbol NSE
PIT disclosures with explicit informational direction, and RupeeVest monthly
mutual-fund stock flows visibly labelled third-party. See `CODEX-HANDOFF.md`
for the restart checkpoint and `ARCHITECTURE.md` for the flow boundary.

## Manual refresh control

The top-right `Refresh` control calls the localhost TrendForge API, which runs
every currently registered source through the existing MD69 collector. The UI
shows the dynamic source count and 09:00, 09:17, 10:30, 12:30, 13:30 and 15:00
IST schedule. After a committed run, all three panels reload from saved files;
failed sources keep their prior last-good file and real timestamp.

## MD69 69-source reliability status

MD69-M1 through M7 are complete in `D:\TrendForge`. They provide one
due-only collector, atomic normalized storage, manifests, health, retention,
timestamp alignment and a canonical panel bridge. The safe run produced 69
unique manifest and health rows with no network call.

Automatic collection is now active through one Windows logon task. Schedules
remain provisional and readiness remains false; the approval does not make
timing official. The static catalog still shows cached JSON, while the
TrendForge backend now stores canonical normalized manifests for live panels.

Closed-session bridge repair (2026-08-05): panels now read the latest canonical
manifest after close and expose same-day saved inputs as `RESEARCH_ONLY` with
the actual fetch timestamp. Old calculation samples are cleared before merge,
so they cannot override the current EOD bhavcopy. Missing current feeds fail
closed: sector data is unavailable when today's `nse_all_indices` was not
collected rather than silently showing an older sector table.

**Root:** `D:\trendforge_inventory_app`  
**Product:** market-source inventory catalog (141 rows / ~98 primaries), sample screener tables, cross-board consensus strip  
**Stack:** Static SPA (HTML/CSS/JS) + Python data generator/diagnostics  
**Data snapshot:** `links_105.json` (Excel/`generate_json.py` and/or merge + **fill_catalog_samples_from_collector.py**)  
**Add a new link (full process):** [`ARCHITECTURE.md`](./ARCHITECTURE.md) **§15**  
**Feed bar + Path A/B samples:** same doc §16–§17 · ops §8: `MD69_REFRESH_OPERATION_REFERENCE.md`

---

## Quick navigation

| Doc | Purpose |
|-----|---------|
| [README.md](./README.md) | Run, legend, features |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Layers, consensus; **§15 add-link process**, **§16 feed bar**, **§17 Path A/B** |
| [GRAPH.md](./GRAPH.md) | System / data / consensus / dependency graphs |
| [SCREENER.md](./SCREENER.md) | **Symbol screener engine** (feature table, extractors, think-engine hooks) |
| [CODEX-HANDOFF.md](./CODEX-HANDOFF.md) | **Codex / AI start file** — done, next tasks, APIs, gotchas, paste prompt |
| [MD69 operation reference](../TrendForge/docs/fable/MD69_REFRESH_OPERATION_REFERENCE.md) | Verified upstream refresh flow, source add/remove procedure, code map and tests |
| [INDEX.md](./INDEX.md) | This file — full file map + **usefulness audit** |
| [index_file.md](./index_file.md) | **Per-file index** — purpose, work, keep/remove for cleanup |
| → [Screener usefulness audit](#screener-usefulness-audit-canonical) | A/B/C/D verified counts (stock screener + cross-board) |
| → [Consensus UI (two strips)](#consensus-ui-two-strips) | Cross-Board vs Nifty filter — score / order / select / show |
| [docs/CONSENSUS_SOURCE_LINKS.md](./docs/CONSENSUS_SOURCE_LINKS.md) | **Which links vote (13→22), +9 added, why rest skipped** |
| [docs/ADD_40_SCREENER_LINKS_PLAN.md](./docs/ADD_40_SCREENER_LINKS_PLAN.md) | **Next 40+ links** (on top of 99) — plan pointer |
| TrendForge `ADD_40_SCREENER_LINKS_PLAN.md` | Full 1–40 tables + workflow + intake log |

**Run UI:** `python -m http.server 8080` → http://localhost:8080/

---

## Sector Bull / Bear Pulse

The compact panel immediately above Consensus v4 derives five strongest and
five weakest sectors from the existing `nse_all_indices` snapshot. It covers
the supplied 38-name sector/thematic allowlist, exposes full row details on
expand, and shows an explicit daily snapshot/stale state. It does not add a
source link, stock score or consensus vote.

---

## Live inventory snapshot (from `links_105.json`)

| Metric | Count |
|--------|------:|
| Inventory rows (links) | **165** |
| Unique `active_source_keys` (pipe-split) | **129** |
| `status = STRONG` | **118** |
| `status = SUPPORTING` | **6** |
| `status = THIRD_PARTY` | **5** |
| `status = PROVENANCE` | **22** |
| `status = COMPANION` | **11** |
| `status = CONTEXT_NEWS` | **3** |
| `screener_integration = LINKED_RESEARCH_SCREENER` | **83** |
| `screener_integration = INFO_ONLY_ZERO_SCORE` | **4** |
| `RESEARCH_CONTEXT_ONLY` | **30** |
| `GATE_DEPENDENCY` | **28** |
| `SCANNER_OPERATIONAL_INPUT` | **7** |

> **Note:** The filename `links_105.json` is retained only for compatibility.
> **158 rows are not 158 independent feeds**; mirrors and companions resolve to
> 122 pipe-split logical keys.

### Topics

| Topic | Rows |
|-------|-----:|
| Ownership & Insider | 17 |
| Commodity / MCX / Global | 16 |
| Calendar / Regime | 18 |
| Derivatives & Options | 18 |
| Price & Universe | 12 |
| Deals | 8 |
| News / Catalyst | 7 |
| Institutional Flow | 7 |
| Macro | 4 |
| Surveillance | 5 |

---

## Screener usefulness audit (canonical)

**Base classification audited against the 105-row snapshot on 2026-08-03; the seven-feed v1.3 extension was verified on 2026-08-04.**  
**Purpose:** how many of 105 links give stock/contract name + market details for screener and cross-board — **not** the same as `status=STRONG`.

The added rows are supporting evidence, not new consensus voters: T2T and PR
events add B/risk context; lot schedules and most-active F&O add C context;
board meetings and IPO rows add event/calendar context. The historical 105-row
A/B/C/D table below is retained as its dated audit rather than silently
reclassifying old rows. Current catalog totals are 112/76 as shown above.

### Definition of “useful”

| Class | Meaning | Screener role | Cross-board role |
|-------|---------|---------------|------------------|
| **A** | Stock name + LTP / % / volume / gap (classic movers + cash bhavcopy) | Best Top-N pick rails | Momentum voters |
| **B** | Stock name + special details (deals, pledge, PIT, OI spurts, ASM/GSM, SLB, actions) | Filters / risk / flow | Flow + risk voters |
| **C** | F&O / options / MCX contracts (symbol, strike, OI, volume when present) | Derivatives tables | Limited (OI/volume only) |
| **D** | Macro, FII totals, calendar, news, gold/EIA/CFTC, AMFI | Context only | **Not** stock Top-5 boards |

### Verified counts (105 rows)

| Class | Rows | Unique primaries | Notes |
|-------|-----:|-----------------:|-------|
| **A classic movers** | **12** | **10 keys** | Claim “~12 / 10 feeds” — **TRUE** |
| **A broader** (+ equity universe, Nifty500, all indices) | **16** | **13** | Identity/universe — weaker “pick movers” |
| **B special** | **43** | **20** | Claim “~43” — **TRUE** |
| **C options/F&O/MCX** | **11** | **9** | Claim “~9” — **TRUE** as feeds; 11 rows with mirrors |
| **D context** | **35** | **20** | Claim “~38” — **≈ TRUE** (3 high) |
| **A+B+C stock/contract useful** | **70** | **42 primaries · 48 keys** | Claim “~66 / ~36 boards” — **≈ TRUE** |
| **Greeks (delta/γ/θ/ν/IV)** | **0** | — | Claim “no greeks” — **TRUE** |

```
105 inventory link rows
 ├─ ~70  → stock/contract screener-useful (A+B+C)
 │         → ~42 unique primaries / ~48 unique keys
 │         (mirrors share data — not 70 independent boards)
 ├─  12  → classic volume / % / gap / most-active / bhavcopy (10 feeds)
 ├─  11  → options/F&O/MCX rows (9 primaries; OI/volume; NOT greeks)
 └─  35  → context / macro / news / calendar (not stock Top-5)

status=STRONG = 68  ≠  68 good stock pickers
(master SCREENER_STRONG_DATA ≈ 61 keys includes macro/NAV “strong data”)
```

### A — Classic movers (12 rows / 10 feeds)

| Feed (`source_key`) | Rows | Name | LTP | % | Vol | Gap |
|---------------------|-----:|:----:|:---:|:-:|:---:|:---:|
| `nse_variations_gainers` | 1 | ✓ | ✓ | ✓ | ✓ | |
| `nse_variations_loosers` | 1 | ✓ | ✓ | ✓ | ✓ | |
| `nse_volume_gainers` | 1 | ✓ | ✓ | ✓ | ✓ | |
| `nse_most_active_value` | 1 | ✓ | ✓ | ✓ | ✓ | |
| `nse_most_active_volume` | 1 | ✓ | ✓ | ✓ | ✓ | |
| `nse_most_active_underlying` | 1 | ✓ | | | ✓ | |
| `nse_preopen_fo` | 1 | ✓ | ✓ | ✓* | ✓ | ✓ |
| `nse_bhavcopy_eod` | 2 | ✓ | ✓ | | ✓ | |
| `bse_bhavcopy_eod` | 2 | ✓ | ✓ | | ✓ | |
| `nse_sector_constituents` | 1 | ✓ | ✓ | ✓ | ✓ | |

\* Pre-open gap % from IEP / previous close.

**Broader A (+4 rows, not classic movers):** `nse_equity_universe` (2), `nse_nifty500_constituents` (1), `nse_all_indices` (1).

### B — Special stock details (43 rows)

| Group | Example keys | Notes |
|-------|--------------|--------|
| Deals | `bse_bulk_deals`, `bse_block_deals`, `nse_large_deals`, `nse_large_deals_snapshot`, `nse_block_deal` | Strong cross-board flow |
| Ownership | `bse_sast`, `*_pledge_data`, `nse_regulation_29/31`, `nse_shareholding_pattern` | Many sparse samples |
| Insider | `nse_pit_symbol` (+ `nse_pit_current` pipe) | Thin / ESOP-heavy samples |
| OI spurts | `nse_oi_spurts`, `nse_oi_spurts_contracts` | Good OI filter |
| Surveillance | `nse_asm`, `nse_gsm` | Risk rail, not pure short signal |
| SLB | `nse_slb` | Borrow-pressure context |
| Actions / results | `nse_corporate_filings_actions`, `nse_daily_buyback`, `nse_financial_results` | Weaker pickers |

### C — Options / F&O (11 rows / 9 primaries)

| Feed | Notes |
|------|--------|
| Live BankNifty / Nifty / stock fut+opt | Symbol, expiry, strike, CE/PE, LTP, vol, OI when present |
| `nse_fo_bhavcopy` (+ `nse_participant_oi`) | EOD F&O |
| `nse_option_chain_equity` (+ `nse_option_chain`) | Often **empty** sample |
| `mcx_bhavcopy` | Commodity contracts — not NSE equity |

**Greeks:** none of the 105 rows expose delta / gamma / theta / vega / IV in samples.

### D — Not stock Top-5 (35 rows)

FRED, SGE gold, WGC, EIA, CFTC · FII/DII · NSDL FPI · AMFI schemes · trading calendar · market turnover totals · BSE/NSE news announcements.

### Cross-board wiring today (subset of useful)

| Metric | Count |
|--------|------:|
| Rows touching **current** consensus source keys | **19** |
| Unique keys in consensus defaults (present in inventory) | **13** |

Wired: gainers/losers, volume, preopen, large deals, snapshot, bulk/block, PIT, ASM/GSM, block_deal keys.  
**Not wired yet (but B/A useful):** most-active, bhavcopy, OI spurts, SLB, sector, live options — add via `consensus_plugins.js`.

### Caveats

1. **Rows ≠ boards** — same feed appears as API + provenance + companion.  
2. **Useful contract ≠ rich sample** — many B/C rows have `records_sample = 0`.  
3. **`STRONG` (68) ≠ stock picker** — includes macro/commodity structured data.  
4. **No greeks** — options cross-board can only use OI / volume / LTP.

### Related diagrams

See **[GRAPH.md §8](./GRAPH.md)** (verified pies + flowchart).  
Architecture summary: **[ARCHITECTURE.md §6](./ARCHITECTURE.md)**.

---

## File map

### Core runtime (browser)

| File | Role | Depends on |
|------|------|------------|
| `index.html` | App shell, KPIs, consensus strip host, scripts | CSS, JS |
| `styles.css` | Dark Bloomberg-style theme | — |
| `app.js` | Load JSON, filters, cards, drawer, export, schema tables | `links_105.json`, `schemas.js`, `consensus.js` |
| `schemas.js` | Per-source display schema, flatten helpers | — |
| `consensus.js` | Cross-board consensus engine v4 | optional `flattenPreOpen` from schemas |
| `consensus_plugins.js` | Future board registrations (no engine edits) | `consensus.js` |
| `links_105.json` | 105 inventory items + samples | generated |

### Data pipeline (Python)

| File | Role |
|------|------|
| `generate_json.py` | Build `links_105.json` from master Excel + verify CSV + raw paths |

**Upstream (outside this folder):**
- `D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx`
- `D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\VERIFY_ALL_105_WITH_SAMPLES.csv`
- Raw endpoint dumps under `D:\TrendForge\data\raw_sources\...`

### Diagnostics / inspection

| File | Role |
|------|------|
| `diag_consensus2.py` | Consensus policy mirror + board smoke test |
| `diag_consensus.py` | Older consensus probe |
| `diag_deep.py` / `diag_deep2.py` | Deep sample inspection |
| `diag_empty.py` | Empty `records_sample` vs `sample_row` |
| `diag_sample.py` | Problem-source sample keys |
| `diag_out.txt` | Captured diagnostic output |
| `inspect_all.py` | Bulk key listing |
| `inspect_samples.py` | Sample field dumps |
| `inspect_targets.py` | Targeted key search |
| `inspect_cftc_news.py` | CFTC/news inspection |
| `links_catalog.txt` | Catalog export |

### Documentation

| File | Role |
|------|------|
| `README.md` | Entry + runbook |
| `INDEX.md` | This index |
| `ARCHITECTURE.md` | Design |
| `GRAPH.md` | Diagrams |

---

## Inventory item contract (each of 105 rows)

| Field | Meaning |
|-------|---------|
| `row_no` | Stable inventory row number |
| `title` | Human name |
| `active_source_keys` | Pipe-joined source key(s) |
| `canonical_url` / `resolved_url` / `example_url` | Endpoint identity |
| `topic` | Sidebar group |
| `status` | STRONG / PROVENANCE / COMPANION / CONTEXT_NEWS / … |
| `screener_integration` | How TrendForge may use the link |
| `safe_use` / `purpose_jobs` / `next_action` | Governance |
| `usable_rows` | Usability count from verification |
| `sample_fields` | Field tag cloud inputs |
| `sample_row` | First cleaned record (or sole sparse sample) |
| `records_sample` | Up to 250 cleaned records for UI tables / consensus |
| `python_snippet` / `curl_snippet` | Copy-paste fetch helpers |
| `provenance_url` | Human landing page when API has companion web |

---

## Consensus UI (two strips)

Rendered in `#consensus-strip` by `consensus.js` → `renderConsensusStrip(inventory)`.  
Full design: [ARCHITECTURE.md §5](./ARCHITECTURE.md) · graphs: [GRAPH.md §5 / §5b](./GRAPH.md).

### Same calculation (shared)

Both strips use **one** scoring pass:

1. Load each voting board from inventory samples (cached preprocess)  
2. Top-K unique symbols per board → `points = weight × (11 − rank) × sample_quality`  
3. Family decay within side  
4. Dominant BUY/SELL, drop weak mixed ties  
5. Qualify: multi-board **or** multi-family **or** strong single  
6. Sort full lists → `buyRanked` / `sellRanked`  

**Click any pill** → breakdown modal (board votes + inventory links containing that symbol).

### Section 1 — Cross-Board Consensus v4

| Step | Behaviour |
|------|-----------|
| Calculate | Shared pipeline above |
| Order | confidence → families → boards → score |
| Select | All qualified names (any market cap) |
| Show | Top **5 BUY** + top **5 SELL** |

May include small / thin names (pennies) if they top board ranks.

### Section 2 — Nifty filter (Trusted index only)

| Step | Behaviour |
|------|-----------|
| Calculate | **Same scores** (no re-score) |
| Order | **Same ranking** |
| Select | Keep only if symbol ∈ **Nifty universe** |
| Show | Top **5 BUY** + top **5 SELL** after filter |

**Nifty universe** = static **Nifty 50** list ∪ symbols from inventory `nse_nifty500_constituents` (sample ≤250 of ~500).

**One line:** high score alone is not enough — stock must also be on Nifty 50/500.

### Compare (short)

| | Cross-Board | Nifty filter |
|--|-------------|--------------|
| Scores | Same | Same |
| Order | Same | Same |
| Gate | Score rules only | Score rules **+ Nifty membership** |
| Purpose | Full signal (noisy) | Liquid large/mid names |

### Consensus boards (default registry)

Registered at load via `ConsensusEngine.loadDefaultBoards()`:

| Family | Boards (concept) | Typical `sourceKey` |
|--------|------------------|---------------------|
| momentum | Day gainers / losers | `nse_variations_gainers`, `nse_variations_loosers` |
| preopen | Gap up / gap down | `nse_preopen_fo` |
| volume | Spike up / down (by `pChange`) | `nse_volume_gainers` |
| risk | ASM / GSM | `nse_asm`, `nse_gsm` |
| deals | Large / snapshot / bulk / block / NSE block* | `nse_large_deals`, `bse_bulk_deals`, … |
| insider | PIT buy / sell | `nse_pit_symbol` |

\* `nse_block_deal`, `nse_block_deal_live` pre-registered; vote only when samples exist.

**Nifty list source:** `nse_nifty500_constituents` (+ built-in Nifty 50 set in `consensus.js`).

**Extend boards:** `consensus_plugins.js` / `registerConsensusBoard(...)`.

**Gotcha:** Pre-open preprocess must accept **already-flat** rows (`symbol` + `gapPercent`). Nested-only flatten would wipe flat samples and empty the Nifty strip.

---

## Scripts cheat sheet

```bash
# UI
cd D:\trendforge_inventory_app
python -m http.server 8080

# Regenerate inventory JSON (needs upstream Excel/CSV + raws)
python generate_json.py

# Consensus smoke test
python diag_consensus2.py
```

---

## Related systems

| System | Path / note |
|--------|-------------|
| TrendForge data lake | `D:\TrendForge\data\...` |
| This catalog app | `D:\trendforge_inventory_app` |
| Screener SPA | `screener.js` → `#screener-panel` — feature table (A/B/C cached feeds); see [SCREENER.md](./SCREENER.md) |
| Downstream (future) | Think engine via `getSnapshot()` / `onBuild()`; VAYU tools may consume same contract |

---

## Implemented 69-source data foundation

MD69-M1 created the connection instruction card for every one of the 69
primary feeds. The CSV is frozen by SHA-256, while typed YAML profiles connect
each source to an existing endpoint or resolver, required parameter provider,
and parser/normalization adapter.

| Item | Current status |
|---|---|
| Exact registry | 69 rows / 69 unique keys; SHA-256 verified |
| Schedule authority | `PROVISIONAL`; publication timing is not officially verified |
| Production activation | `false` |
| Live downloads in MD69-M1 | None |
| Database migration or scheduler | Not included |
| Compiled adapter matrix | 69/69 contracts |
| Offline MD69-M1 tests | 13 passed |
| Governing plan | [MARKET_DATA_69_CAMPAIGN_PLAN.md](./docs/fable/MARKET_DATA_69_CAMPAIGN_PLAN.md) |
| Registry evidence | [REFRESH_INTERVAL_REVIEW_69.csv](./outputs/refresh-cadence-audit-20260804/REFRESH_INTERVAL_REVIEW_69.csv) |

All fetch/archive/schedule code belongs in `D:\TrendForge`. This inventory SPA
remains display/catalog only.

---

## Change log (docs package)

| Date | Change |
|------|--------|
| 2026-08-03 | Added INDEX / ARCHITECTURE / GRAPH; README counts + consensus v4 notes |
| 2026-08-03 | Canonical **screener usefulness audit** (A/B/C/D verified vs `links_105.json`); GRAPH §8 + ARCH §6 + README updated |
| 2026-08-03 | Dual consensus UI: **Cross-Board** + **Nifty filter** strip; docs + GRAPH §5b |
| 2026-08-03 | Screener Task A: 14 B/C deal, risk, PIT/SLB, OI and F&O extractors; deterministic fixture + real-inventory verification |
| 2026-08-03 | Screener v1.2 correction: A-only score policy; signed deal/OI evidence; PIT direction neutrality; contextual ASM/GSM parsing; financial golden tests |
| 2026-08-04 | Added guarded `trendforge.livePanels.v1` bridge: shared Sector/Consensus/Screener snapshot, <=300s/current-date gate, immutable overlay, and no static price/vote fallback |
| 2026-08-05 | Implemented and verified MD69-M1: exact registry/hash, 69/69 typed adapter matrix, compiler, provisional activation gate, and zero-network tests |
| 2026-08-11 | Synchronized five-route `NOT_IN_USE` quarantine, working replacements, 119 registry keys, 161/125 catalog shape and 18-test proof |

## Live panel status

The 112-row catalog remains `links_105.json`. Panel calculations use `live_panels.js` and the localhost TrendForge API. `LIVE` is allowed only for the current trading date and the panel's complete critical-source set. During an open session, `OFFLINE`, `WAIT`, and `STALE` block saved price/voting samples. After close, `MARKET_CLOSED` may show the latest saved samples for clearly red-labelled research only; the shared status also shows the latest source time or panel-job time.

*When inventory is regenerated, re-check counts in this INDEX against `links_105.json`.*

## Dead links retained as hints only (2026-08-11)

Five verified dead/unusable routes are marked `NOT_IN_USE`: Yahoo `^BADI`,
`pytrends`, StockEdge "API", BSE `FIIDII/w`, and BSE
`ParticipantWiseOI/w`. They are absent from active catalog/source keys and
cannot fetch, schedule, score, or vote. Their working replacements remain
active. MCX is not in this list because it is intermittent rather than dead.

Current observed shape after this documentation-only sync: **119/119** typed
TrendForge registry keys and **161 catalog rows / 125 active logical keys**.
The quarantine did not change those counts.

Authority and tests:

- `D:\TrendForge\config\source_route_quarantine.yaml`
- `D:\TrendForge\docs\fable\DEAD_SOURCE_ROUTE_QUARANTINE_20260811.md`
- `D:\TrendForge\backend\tests\test_dead_source_route_quarantine.py`

## FII-related stock-name evidence

The compact panel below Nifty Filter reads
`GET /api/institutional/fii-stock-signals` from TrendForge. It shows saved
bulk/block stock names as `LARGE_DEAL` evidence and quarterly FII/FPI holding
changes only when explicit change fields exist. It is informational, zero-vote
and zero-score. After manual Refresh completes, it reloads with the other panel
consumers from canonical saved objects and shows the saved fetch timestamp.
Current observed output after the 2026-08-13 refresh is 349 deal rows, 462
holding-change/reference rows and 351 resolved symbols. Governing plan:
`D:\TrendForge\docs\fable\FII_STOCK_SIGNALS_PLAN.md`.
Observed integration evidence: `docs/fable/FII_REFRESH_INTEGRATION_2026-08-11.md`.

Third-party FII holding screens (Screener.in, Tickertape `forInstHldng3M`, Dhan
`FIIHLDChagPer`, Equitymaster) are on MD69 Refresh (pin **123**) and catalog
cards 162–165. Last-good 2026-08-13: 105 / 300 / 32 / 25 rows. The **inventory**
FII strip shows all four (identity: ticker/ISIN, exact name, or NAME ONLY).
The **TrendForge command room** does not consume the API yet (`TF-APP-FII-M1`).
Not daily FII buy/sell. Not voters. Canonical:
`ADD_40_SCREENER_LINKS_PLAN.md` intake 2026-08-12.


## Source Operations panel - 2026-08-15

The TrendForge Inventory button opens `/inventory-workbench/?embed=terminal`.
The panel below the KPI cards is an operational source-health view, not another
screener. It reads compiler, monitor, fetch-attempt, parser-output, and
freshness APIs and shows the path from registered contracts to research-usable
facts.

It names each source state (`HEALTHY`, `VALID_EMPTY`, `STALE_PARTIAL`,
`BLOCKED`, `FAILED`, `NOT_ATTEMPTED`), reason, proof/data date, and research
effect. It keeps valid-empty separate from failed and never converts HTTP
success or catalog presence into a vote. It cannot rank, activate, confirm,
calculate quantity, or place orders. Standalone catalog behavior is unchanged.


## Hash-pin caveat - 2026-08-15

The source and bundled runtime files contain aligned feature markers but are separate revisions and are not byte-identical for this
change, but the existing snapshot manifest still contains the pre-Source-
Operations byte sizes and hashes. The existing `inventory-workbench.test.js`
also still expects the old drawer URL without `embed=terminal`. Its current
observed result is **FAIL: Size mismatch: index.html**. This means the runtime
panel observation is valid, but the manifest/test pin must be refreshed before
claiming a clean snapshot-integrity verdict. No source data, catalog sample, or
TrendForge state authority is affected by this metadata/test discrepancy.

## Post-commit bridge documentation - 2026-08-15

Refresh and Scheduler commit source data first. Only a schema-valid cash-relevant last-good save starts the existing A1-C1 research path. The embedded Source Operations panel reads the resulting two-track snapshot: source health/lineage and cash pipeline stage status.

No HTTP 200, catalog sample, valid-empty context or unrelated source refresh can create a cash rank. The UI remains research-only and keeps activation, CONFIRMED, quantity and execution locked. Snapshot manifest/hash reconciliation is a separate integrity task.
