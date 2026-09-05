# TrendForge Inventory App — Architecture

## Official BSE/RBI and calculated-output handoff (current, 2026-08-11)

The upstream TrendForge registry now has **123** source contracts. The baked
Inventory catalog has **165 cards / 129 logical keys** and contains populated
cards for `bse_financial_results_xbrl` (5,126 rows),
`bse_shareholding_pattern` (5,508 rows), and `rbi_tbill_yield` (3 rows).
The SPA remains display-only and never calls BSE or RBI.

TrendForge also materializes four internal calculation contracts. Industry
peers (500), option Greeks (65), and the first prospective PCR/Max-Pain
observation (1) are saved upstream, but are not source links, voters, Screener
score terms, or catalog cards. `fundamental_ratios_v1` is fail-closed and has no
saved rows because the current BSE feed is filing discovery, not numeric iXBRL
facts. This boundary prevents metadata from becoming invented ratios.

## Files 1-7 recovery handoff (historical checkpoint, 2026-08-11)

TrendForge—not this SPA—owns the 77-route recovery plane. The exact ledger is
`D:\TrendForge\docs\fable\evidence\FREE_SOURCE_RECOVERY_77_MATRIX_20260811.csv`.
That checkpoint used **158 cards / 122 logical keys**. Newly populated
AMFI AUM, LME fallback, EIA STEO and OPEC adjustment rows are visible through
the normal catalog path.

Fifteen free Upstox Analytics contracts are code-ready upstream but are not
added as populated catalog cards until a user token produces archived,
schema-valid rows. The browser never sees the token and never calls Upstox.
ATM-IV rank remains a derived WAIT state until 252 archived sessions; neither it
nor any new recovery feed changes Consensus or Screener scoring.

## Packs 6-7 option-data handoff (historical checkpoint, 2026-08-11)

The Inventory still performs no provider fetch. Pack 6 repaired TrendForge's
existing NSE option-chain parser so symbol/expiry may be recovered from the
request URL and incomplete identities fail closed. Pack 7 added no source key:
credentialed analytics/broker routes remain blocked and synthetic Greeks are
rejected. The SPA consumes only the same persisted catalog/overlay contracts.

## Pack 5 catalog handoff (historical checkpoint, 2026-08-11)

The Inventory remains display-only. TrendForge persisted Pack-5 last-good
objects first; `merge_registry_into_catalog.py` then created cards and
`fill_catalog_samples_from_collector.py` baked bounded samples. The filler now
preserves raw archive path/hash, fetched timestamp, source row count, normalized
count, real parser version and third-party trust. Its historical snapshot was
154 rows / 118 logical keys; no browser-to-provider fetch was added.

## Manual refresh boundary

The SPA owns only the `Refresh` control and status display. It sends one
localhost request to TrendForge and never contacts NSE/BSE. TrendForge selects
all sources from its registry, serializes competing runs with the existing
lease, commits normalized files/manifests, then the SPA rereads the canonical
panel snapshot. Saved stale data remains usable for research without gaining a
`LIVE` label.

The exact code and extension procedure is in
[MD69_REFRESH_OPERATION_REFERENCE.md](../TrendForge/docs/fable/MD69_REFRESH_OPERATION_REFERENCE.md).
The browser has no hard-coded source count. The current registry release is
deliberately hash- and exact-count-pinned, so adding/removing a source requires
a controlled CSV/YAML/hash/compiler/test update rather than a silent runtime
change.

## MD69 canonical data boundary — collector path and activation status

`D:\TrendForge` now contains MD69-M1 through M7 plus a controlled expansion of
the collector registry to **99** source keys (filename still
`source_refresh_registry_69.csv` for path compatibility). Due-only
orchestration, content-addressed storage, manifests/health, timestamp
alignment, and a cloned panel bridge remain the only collection plane. The
inventory browser remains a static consumer and never downloads NSE/BSE
directly.

Schedules remain provisional and readiness remains false. The named Windows task
was not found during the 2026-08-06 audit, so automatic execution is not claimed
until the task is recreated and observed. The static catalog still reads
`links_105.json`; only panels connected to the TrendForge live API can consume
canonical manifests.

**Version:** 2.1 (Consensus engine v4 + 99-source registry / catalog merge)  
**App type:** Static single-page application (SPA) + offline data pipeline  
**Primary artifact:** `links_105.json` — compatibility filename; **141** inventory
rows / ~**98** collapsed primaries after registry merge (2026-08-06)

---

## 1. Goals

1. **Catalog** every linked market source with honest status and safe-use rules.  
2. **Inspect** sample records with schema-driven tables (not raw JSON only).  
3. **Screen** top symbols where samples allow (ranked / latest / pos-neg modes).  
4. **Consensus** — cross-board BUY/SELL scores from multiple feeds (cached samples).  
5. **Future-proof** — add new inventory keys via registry plugins, not engine rewrites.

Non-goals:

- Live multi-exchange streaming  
- Order placement  
- Greeks computation from incomplete option-chain contracts  
- Treating news as price proof  

---

## 2. High-level layers

```
┌─────────────────────────────────────────────────────────────┐
│  UPSTREAM (TrendForge data plane)                           │
│  Excel master · verify CSV · raw endpoint dumps             │
└───────────────────────────┬─────────────────────────────────┘
                            │ generate_json.py
┌───────────────────────────▼─────────────────────────────────┐
│  SNAPSHOT                                                   │
│  links_105.json  (141 items post-merge; samples Path A)     │
└───────────────────────────┬─────────────────────────────────┘
                            │ fetch()  catalog cards use this only
┌───────────────────────────▼─────────────────────────────────┐
│  PRESENTATION (browser)                                     │
│  index.html · styles.css · app.js  (#results-count, cards)  │
│  schemas.js · consensus.js · screener.js · live_panels.js   │
│  live_panels clones inventory + overlay → 3 panels only     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Upstream → snapshot pipeline

### Inputs

| Input | Role |
|-------|------|
| `SOURCE_LINK_INVENTORY_MASTER.xlsx` | Sheets: `LINKED_SOURCES`, `SCREENER_STRONG_DATA`, `SCREENER_CONTEXT_ONLY`, evidence |
| `VERIFY_ALL_112_WITH_SAMPLES.csv` | Per-source-key + URL verification and samples |
| Raw files under `raw_path` | Full records for `records_sample` |

### Process (`generate_json.py`)

1. Join on stable `(active_source_keys, canonical_url)` identity with unique-URL compatibility fallback.  
2. Assign `title`, `topic`, `status` from keys + row rules.  
3. Map API ↔ provenance HTML companions.  
4. Parse raw dumps → cleaned records (field transforms per key).  
5. Emit full normalized records for engine-enabled feeds and a maximum-250 display sample for other feeds.
6. Emit `records_scope`, source/normalized counts, parser version and content hash; reject duplicate primary identity.

### Output item shape (contract)

```text
Identity     row_no, title, active_source_keys, *urls
Classification  topic, status, mode, screener_integration
Governance   safe_use, purpose_jobs, next_action, source_role
Samples      sample_fields, sample_row, records_sample[], entity_*
Ops          raw_path, python_snippet, curl_snippet, freshness_*, parser_*
```

**Invariant:** UI never invents market fields; it only displays what samples contain.

---

## 4. Frontend architecture

### Boot sequence (verified against `app.js` + `live_panels.js`)

```
DOMContentLoaded
  → fetch links_105.json
  → initApp()
       → window.inventory = inventory          // catalog only; never mutated by panels
       → renderKPIs / sidebar / cards (catalog)
       → LivePanelsController.start(inventory)
            → GET http://127.0.0.1:8000/api/panels/live
            → clone catalog; strip static calculation samples
            → apply inventoryOverlay by source_key
            → renderSectorScreenerPanel(merged)
            → renderConsensusStrip(merged)
            → renderScreenerPanel(merged)
            → poll every 60s while tab visible
```

If `LivePanelsController` is missing: panels show WAIT and **block** cached calculations
(no silent score/vote from old `links_105.json` prices).

### Script load order (`index.html`)

1. `schemas.js` — `LINK_SCHEMAS`, `flattenPreOpen`, …  
2. `consensus.js` — engine + defaults  
3. `consensus_plugins.js` — optional extra boards  
4. `screener.js` — symbol feature table + extractors  
5. `sector_screener.js` — sector context only  
6. `live_panels.js` — TrendForge bridge + fail-closed merge  
7. `app.js` — orchestration (starts live controller last)

### `app.js` responsibilities

| Concern | Behavior |
|---------|----------|
| State | `inventory`, topic, status KPI, field tag, search, sort, view mode |
| Filter | Topic × status × tag × search query |
| Render | Grid cards or table (catalog snapshot) |
| Drawer | Full metadata + JSON sample + snippets |
| Schema tables | `getSchemaForItem` → ranked/latest views |
| Export | Visible rows CSV; per-item dataset CSV |
| Live panels | Starts `LivePanelsController` only — does **not** call sector/consensus/screener directly |

### `schemas.js` responsibilities

- Registry keyed by `active_source_keys` (or first matching pipe key).  
- Modes: `RANKED`, `LATEST_5`, `POSITIVE_AND_NEGATIVE`, `STATUS_ONLY`, `MIRROR_POINTER`, …  
- Flatteners for nested payloads (pre-open, OI spurts, turnover).  
- Display columns + sort + optional `derive`.  

### Status model (UI badges)

| Status | Meaning |
|--------|---------|
| `STRONG` | Structured market sample usable as evidence |
| `CONTEXT_NEWS` | Catalyst only |
| `PROVENANCE` | Human landing / non-API identity |
| `COMPANION` | Backup when primary empty |
| `VALID_EMPTY` / `SOFT_EMPTY` / `BLOCKED` | Contract connected but empty or restricted |

---

## 5. Consensus engine v4

### Stock voters currently wired (Cross-Board + Nifty share scores)

Nifty filter does **not** re-score — it intersects the same ranked lists with the
official Nifty 500 membership set (≤5 per side).

| Family | Source keys (examples) | Role |
|--------|------------------------|------|
| momentum | `nse_variations_gainers/loosers`, `nse_bhavcopy_eod` | Day % move |
| preopen | `nse_preopen_fo`, **`nse_preopen_cash`** | Gap up/down |
| volume | `nse_volume_gainers`, **`nse_most_active_volume/value`** | Volume / value spikes |
| deals | `nse_large_deals*`, block deals, BSE bulk/block, **`nse_bulk_deals_today_csv`** | Institutional deals |
| insider | `nse_pit_symbol` | Insider PIT buy/sell |
| risk | ASM/GSM, **`nse_fno_ban`** | Surveillance / ban |
| delivery | **`nse_mto_delivery`** | High / low delivery % |
| short | **`nse_short_selling`** | Short interest (SELL rail) |
| derivatives_oi | **`nse_oi_spurts`** (stock underlyings only) | OI spurts |

**Not stock voters** (no per-stock symbol in samples): market FII/DII totals
(`nse_fii_dii`), AMFI NAV schemes (`amfi_nav`), sector FPI AUC tables, pure news.
Third-party FII holding screens (`screener_in_fii_holding_change`,
`tickertape_fii_holding_change_3m`, `dhan_fii_holding_change`,
`equitymaster_fii_buys_reference`) are MD69-collected INFO sources (pin 123)
with populated catalog cards. All four appear on the FII strip through verified
ticker/ISIN, exact unique-name mapping, or a visible `NAME ONLY` identity.
Lagged hold-%/reference evidence, **not** daily FII tape, **not** voters.
Canonical table: `D:\TrendForge\docs\fable\ADD_40_SCREENER_LINKS_PLAN.md` intake 2026-08-12.

**Full list, previous vs current counts, and skip reasons:**  
[`docs/CONSENSUS_SOURCE_LINKS.md`](./docs/CONSENSUS_SOURCE_LINKS.md) (13→22 links, +9 added, why remaining catalog links are not voters).

Add more via `registerConsensusBoard` / factories in `consensus.js` or
`consensus_plugins.js` — do not invent a second scoring formula.

### Design principles

| Principle | Implementation |
|-----------|----------------|
| Efficient | Index inventory by `sourceKey` once; cache preprocess per key |
| Robust | Field alias lists; soft-fail filters; quality × sparse samples |
| Future-proof | `registerConsensusBoard` + factories; plugins file |
| Honest | Multi-board preference; mixed-edge kill; family decay |

### Module map (`consensus.js`)

```
CONFIG              policy knobs (K, thresholds, decay)
utils               num, firstField, side detect, stageRank
METRICS             named metric functions (dealValueCr, pctChange, …)
PREPROCESSORS       preopen, identity, custom via registerPreprocessor
ConsensusBoards     factories: dealPair, momentum, volumeSpike, …
boardRegistry       Map<id, boardDef>
computeConsensus    pipeline
render / modal      strip UI
```

### Scoring pipeline (single shared pass)

```
inventory
  → indexInventory(sourceKey → item)
  → for each enabled board:
        loadSource (cached) → preprocess → rowFilter → metric
        → sort → top K unique symbols
        → points = weight × (K+1−rank) × sample_quality
  → per symbol:
        family_decay within side
        dominant side from net score
        drop mixed if |net|/sum < mixedNetEdge
        qualify: multi-board | multi-family | strong single
  → rank by confidence → families → boards → score
  → buyRanked[] / sellRanked[]   (full ordered lists)
  → Section 1: top 5 of each list (any symbol)
  → Section 2: filter lists to Nifty universe, then top 5
```

### UI: two consensus strips (same scores)

| | **Section 1 — Cross-Board Consensus v4** | **Section 2 — Nifty filter** |
|--|------------------------------------------|------------------------------|
| DOM | Top half of `#consensus-strip` | Bottom half (border-top) |
| Calculate | Shared `computeConsensus` | **No re-score** |
| Order | Shared sort | **Same order** |
| Select | All qualified symbols | Qualified **∩ Nifty set** |
| Show | Top 5 BUY + top 5 SELL | Top 5 BUY + top 5 SELL after filter |
| Risk | May include penny / thin names | Prefer large/mid index names |

**Nifty universe builder** (`buildNiftyUniverse`):

1. Start with static **Nifty 50** symbol set in `consensus.js`  
2. Union symbols from inventory key `nse_nifty500_constituents` (`Symbol` field + `entity_list`)  
3. Membership = Nifty 50 **or** Nifty 500 (sample) — treated as trusted index list  

**Why full ranked lists:** if only top-5 global names were filtered, pennies can occupy all five slots and Nifty section would look empty even when INFY/HYUNDAI ranked #6+.

**Preopen preprocess rule:** if samples are already flat (`symbol` + `gapPercent`, no `metadata`), pass through. Nested-only flatten would zero preopen votes and empty Nifty pills.

**Click pill:** `showConsensusBreakdown(symbol)` — board table + inventory links containing that symbol (verify).

Diagrams: [GRAPH.md §5](./GRAPH.md) and [§5b dual strip](./GRAPH.md#5b-dual-strip-cross-board-vs-nifty-filter).

### Sample quality

| Condition | Quality factor |
|-----------|----------------|
| Only `sample_row` / universe ≤ 1 | 0.35 |
| Valid rows &lt; K | max(0.25, n/K) |
| Full depth | 1.0 |

### Family decay

Same economic family (e.g. all `deals`) applies `[1.0, 0.45, 0.25, 0.15]` to ordered board hits so snapshot + large deals do not stack freely.

### Adding a future link (no engine edit)

```javascript
// consensus_plugins.js
registerConsensusBoards(ConsensusBoards.dealPair({
  sourceKey: 'nse_block_deal',
  label: 'NSE Block Deal',
  symbolFields: ['symbol', 'Symbol'],
  sideField: 'Buy/Sell',
  weight: 2.0
}));

// custom metric
ConsensusEngine.registerMetric('myMetric', row => /* number|null */);
registerConsensusBoard({ id, sourceKey, side, family, weight, label,
  symbolFields: [...], metric: 'myMetric', sortDir: 'desc' });
```

Board config contract:

```text
id, sourceKey, side(BUY|SELL), family, weight, label
symbolFields[] | symbolField
metric | metricField
sortDir, preprocess?, rowFilter?, enabled?, minMetric?, maxMetric?
```

### Unmapped sources

`computeConsensus` returns `unmappedSources`: inventory keys with no registered board — candidates for plugins.

---

## 6. Screener usefulness model (architecture view)

Not all 112 current catalog rows are “pick this stock” boards. The usefulness
table below is a historical 105-row audit snapshot; the current catalog/linkage
counts are documented in §15.  
**Canonical verified audit:** [INDEX.md — Screener usefulness audit](./INDEX.md#screener-usefulness-audit-canonical) · diagrams [GRAPH.md §8](./GRAPH.md).

| Class | Live rows | Unique | Role | Cross-board |
|-------|----------:|-------:|------|-------------|
| **A classic movers** | 12 | 10 keys | Name + LTP/%/vol/gap | Momentum (partially wired) |
| **A broader** | +4 | identity | Universe / indices | Usually not Top-5 voters |
| **B special** | 43 | 20 primaries | Deals, pledge, PIT, ASM/GSM, OI, SLB | Flow/risk (partially wired) |
| **C F&O/options** | 11 | 9 primaries | OI/vol/strike; **no greeks** | Limited |
| **D context** | 35 | 20 primaries | Macro, FII, news, calendar | No stock Top-5 |
| **A+B+C useful** | **70** | **42 / 48 keys** | Stock/contract screener | Subset only |

| Policy fact | Value |
|-------------|------:|
| Greeks in inventory samples | **0** |
| Rows on current consensus keys | **19** |
| Unique keys wired in `consensus.js` defaults | **13** |
| Live `status=STRONG` | **68** (≠ stock pickers) |

Master sheet **SCREENER_STRONG_DATA** ≈ strong structured data (includes macro/NAV).  
**STRONG status ≠ stock Top-5 picker.** Extend voters via `consensus_plugins.js`.

---

## 7. Security & integrity

| Concern | Approach |
|---------|----------|
| XSS in consensus UI | `esc()` on symbols/labels; `JSON.stringify` in onclick |
| Field invention | Metrics only from sample fields / aliases |
| Governance | `safe_use` text shown in drawer; news not treated as price |
| Offline sample trust | Footer: scores from cached inventory, not real-time |

---

## 8. Performance

| Path | Complexity |
|------|------------|
| Initial JSON load | ~27 MB once (network + parse) |
| Filter/render | O(N) over 112 current cards |
| Consensus | O(boards × sample_rows); source cache shares preprocess |
| Schema table | O(sample_rows) per opened card |

---

## 9. Extension points

| Extension | Where |
|-----------|--------|
| New inventory row | Upstream Excel → `generate_json.py` |
| New table UI | `schemas.js` `LINK_SCHEMAS[key]` |
| New consensus voter | `consensus_plugins.js` or `registerConsensusBoard` |
| New metric type | `ConsensusEngine.registerMetric` |
| New nested flatten | `schemas.js` + `registerPreprocessor` |
| Topic/KPI change | `app.js` topic order + `generate_json.assign_topic` |

---

## 10. Diagnostics architecture

| Script | Layer |
|--------|--------|
| `diag_consensus2.py` | Mirrors scoring policy; lists unmapped keys |
| `inspect_*` | Field-level inventory archaeology |
| Browser console | `computeConsensus(inventory)`, `listConsensusBoards()` |

JS engine is **source of truth** for UI; Python diag is a policy smoke mirror.

---

## 11. Deployment

```bash
cd D:\trendforge_inventory_app
python -m http.server 8080
```

Serve the folder as static files (any static host). No backend required for read-only catalog.

Regenerate data only when upstream verification set updates:

```bash
python generate_json.py
```

---

## 12. Related documents

- [INDEX.md](./INDEX.md) — file map & live counts  
- [GRAPH.md](./GRAPH.md) — diagrams  
- [README.md](./README.md) — operator runbook  

## 13. Live panel input plane

`live_panels.js` is the only runtime bridge to `D:\TrendForge`:

```text
links_105.json ──> immutable catalog cards/drawers
                         (never mutated)

TrendForge /api/panels/live ──> validate contract/date/age
                              ──> clone catalog
                              ──> strip static calculation rows
                              ──> overlay current rows by source_key
                              ──> Sector / Consensus / Screener
```

All three status badges carry the same snapshot ID and trading date. Non-live panel states receive no calculation overlay.

---

## 14. 69-source registry foundation (MD69-M1)

**Status:** implemented and verified at the registry/compiler boundary. The
collector/API path exists, but the named Windows task was not found during the
2026-08-06 audit; automatic activation is therefore not claimed.

| Project | Responsibility |
|---|---|
| `D:\TrendForge` | Fetch, archive, validate, normalize, schedule, retain, and monitor market data |
| `D:\trendforge_inventory_app` | Display/catalog only; it must not download live NSE/BSE data |

MD69-M1 created one instruction contract for each of the 69 sources. Each
contract identifies the endpoint and normalized keys, existing acquisition
owner, required parameters and provider/fan-out method, parser or adapter,
empty/holiday rules, and response-reuse or session-sharing behavior.

```text
69-source CSV + fixed SHA-256
          |
typed registry compiler + YAML profiles
          |
69/69 executable adapter matrix
     /           |             \
endpoint      resolver       parser/adapter
registry      or monitor     registration
```

Every schedule remains `PROVISIONAL` with `activation_ready=false`.
Compilation proves that all 69 connection instructions are structurally complete;
it does not fetch market data or prove publication times. The 13 MD69-M1 tests
make zero network calls; runtime refresh behavior is covered separately by the
operational/API test suites and must not be inferred from registry compilation.

Governing plan:
[docs/fable/MARKET_DATA_69_CAMPAIGN_PLAN.md](./docs/fable/MARKET_DATA_69_CAMPAIGN_PLAN.md).

## 15. Verified source-linkage model (updated 2026-08-06)

The app has **two different planes** and several product layers. Do not treat
registry count, catalog row count, and “Showing N feeds” as the same number.

| Layer | Source selection | Current verified scope |
|---|---|---:|
| Catalog snapshot | Excel/`generate_json.py` **or** `merge_registry_into_catalog.py` → `links_105.json` | **141** rows; ~**98** collapsed primaries |
| Collector | Compiled CSV/YAML registry (`source_refresh_registry_69.csv`) | **99** endpoint contracts (`EXPECTED_SOURCE_COUNT=99`) |
| Consensus | Dynamic inventory lookup, static board registry | 22 boards / 13 source keys |
| Screener + Nifty filter | Dynamic inventory lookup, static extractor registry and Nifty gate | extractors include 30-pack finish set |
| Sector pulse | Dynamic `nse_all_indices`, static sector-name allowlist | 38 tracked names |
| Live panel bridge | API `inventoryOverlay` by `source_key` into **cloned** panel inventory | P0 + research + any successful normalized keys (bounded) |

Therefore, adding a catalog row alone makes it **visible** but does not make it
a calculation input, and does **not** invent sample rows. New links need an
upstream parser/normalizer, a role decision (catalog only / Screener / Consensus
/ Sector / live), and matching tests. Consensus must use a plugin for a new
independent voter; existing scoring and family decay must not change implicitly.

### Adding a new link — full process (canonical, 2026-08-06)

Do **not** mix these numbers: collector pin **N**, catalog **rows**, SPA
**“Showing N feeds”** (collapsed primaries). SPA never downloads market sites.

#### A. Collector (TrendForge download plane)

| Step | Action | Where |
|------|--------|--------|
| A1 | Choose one lowercase unique `source_key` | — |
| A2 | Wire fetch (endpoint map, resolver multi-step, or existing adapter) | `config.yaml` endpoints · `source_resolver.py` · `phase3_multi_step_fetch.py` |
| A3 | Add structured parser → real `records` (HTTP 200 alone is not success) | `parsers/*` · `source_parser.py` STRUCTURED map |
| A4 | Add CSV registry row (cadence, empty rule, evidence) | `config/source_refresh_registry_69.csv` |
| A5 | Add YAML profile (owner, parser id, validator, fan-out) | `config/source_refresh_profiles.yaml` |
| A6 | Bump pins: `EXPECTED_SOURCE_COUNT`, CSV/YAML `.sha256`, registry key-set pins | `market_data_registry.py` + hash files |
| A7 | Tests: parser fixture, registry compile, intended panel membership | `backend/tests/` |
| A8 | **Restart** API with `MARKET_DATA_69_ENABLED=1` and provisional override | `uvicorn` on `127.0.0.1:8000` |
| A9 | Clear stuck lease if Refresh says `LEASE_HELD` | SQLite `market_data_scheduler_leases` |
| A10 | Run full collect | `POST /api/market-data/refresh` |
| A11 | Verify | Manifest has new `sourceKey`; `market_data_latest` has `object_path` + `normalized_row_count > 0` (or honest valid-empty) |

#### B. Catalog card + samples (inventory SPA Path A)

| Step | Action | Where |
|------|--------|--------|
| B1 | Add missing registry keys as cards | `python merge_registry_into_catalog.py` → `links_105.json` |
| B2 | Confirm registry keys have cards | `tests/catalog_registry_merge.test.js` |
| B3 | Fill empty samples from collector last-good | `python fill_catalog_samples_from_collector.py` |
| B4 | Hard-refresh browser | `http://127.0.0.1:8080/` · `Ctrl+Shift+R` |
| B5 | Check bar | “Showing ~primaries feeds · inventory *rows*” — not hardcoded 69 |

**What B3 does:** only rows with empty `records_sample` /
`REGISTRY_MERGED_AWAITING_SAMPLE`. Copies ≤250 records from
`market_data_latest` → object JSON into `records_sample`, sets
`status=STRONG`, `connection_status=CONNECTED_FRESH_STRUCTURED`, writes
`links_105.json.bak_fill_*`. Never blanks existing STRONG samples.

**Legacy Path A (original ~69-style feeds):** Excel + VERIFY CSV + raw dumps →
`generate_json.py` (or `fix_empty_samples.py` for surgical raw re-parse).

#### C. Optional product roles (never automatic)

| Role | Where | Note |
|------|--------|------|
| Screener field / extractor | `screener.js` | B/C informational unless score policy re-approved |
| Consensus board | `consensus.js` / plugin | Independent voter only; no double-count |
| Live research / P0 list | `live_panels.py` + `live_panels.js` | Affects panel freshness / overlay priority |
| Schema table | `schemas.js` | Nice card tables; optional |

#### D. Ops checklist (copy-paste)

```text
# 1) After code + CSV/YAML + pin update
cd D:\TrendForge\backend
set MARKET_DATA_69_ENABLED=1
set MARKET_DATA_69_PROVISIONAL_OVERRIDE=1
# start uvicorn 127.0.0.1:8000  (one process only)

# 2) Collect
POST http://127.0.0.1:8000/api/market-data/refresh
# wait until COMPLETED; UI: Saved X · fallback Y · failed Z

# 3) Catalog
cd D:\trendforge_inventory_app
python merge_registry_into_catalog.py
python fill_catalog_samples_from_collector.py

# 4) Browser
# http://127.0.0.1:8080/  Ctrl+Shift+R
```

#### E. Common failures

| Symptom | Cause | Fix |
|---------|--------|-----|
| Refresh “failed to fetch” | API down | Start uvicorn with MD69 env flags |
| `LEASE_HELD` | Stuck SQLite lease | Clear `market_data_scheduler_leases`; one API only |
| Still “Showing 69” | Stale `links_105.json` cache | Hard refresh; confirm inventory count in bar |
| Card empty after Refresh | Path A not filled | Run `fill_catalog_samples_from_collector.py` |
| Saved N · fallback M | Some keys used last-good | Check manifest `STALE_LAST_GOOD` errors; repair fetch |

**Hard rule:** registry is hash- and count-pinned (current pin **99**). Expanding
again is a controlled release, not a silent append.

**Next expansion (planned 40+ links, intake one-by-one):**  
`D:\TrendForge\docs\fable\ADD_40_SCREENER_LINKS_PLAN.md`  
(SPA pointer: `docs/ADD_40_SCREENER_LINKS_PLAN.md`)

Authoritative ops twin:  
`D:\TrendForge\docs\fable\MD69_REFRESH_OPERATION_REFERENCE.md` §8 / §8A.

---

## 16. “Showing N feeds” — exact code path (future link-add backtrace)

Use this map when the bar still shows an old number (e.g. 69) or when a new
source must appear as a painted feed.

### Screen (DOM)

| Piece | File | Location |
|-------|------|----------|
| Count text | `index.html` | `#results-count` |
| Cards / table host | `index.html` | `#main-container` |
| Collapse toggle | `index.html` | `#dedupe-toggle-btn` (“Strong feeds only”) |

### Count calculation (`app.js`) — **no hardcoded N**

```text
fetchData()
  → inventory = JSON from links_105.json
  → initApp() → buildSourceGroups(inventory)
  → applyFiltersAndRender()
       filtered = topic × status × tag × search
       displayList = applyDuplicateCollapse(filtered)   // default ON
       #results-count =
         "Showing ${displayList.length} feeds on page (painted …)
          · … · inventory ${inventory.length}"
```

| Symbol | Meaning |
|--------|---------|
| `inventory.length` | Raw catalog rows in `links_105.json` |
| `displayList.length` | **N** in “Showing N feeds” when collapse is on |
| `primarySourceKey(item)` | `String(active_source_keys).split("\|")[0]` — group key |
| `buildSourceGroups` | One champion + twins per key |
| `applyDuplicateCollapse` | Champions only when `collapseDuplicates === true` |
| `uniqueShown` / `multiShown` / `hiddenTwins` | Breakdown in the same string |

**Verified math (disk, post-merge):** 141 rows → ~98 primaries → UI should show
~**98 feeds** / inventory **141** after hard refresh. **69** means a stale
browser cache of pre-merge JSON or an old mental model of the registry size —
not a constant in `app.js`.

### What to edit for future links

| Goal | Edit |
|------|------|
| New painted feed card | Ensure `active_source_keys` on a `links_105.json` row (`merge_registry_into_catalog.py` or full regenerate) |
| Change count string format | `app.js` `applyFiltersAndRender` (`#results-count`) |
| Change “one feed” identity | `primarySourceKey` + `buildSourceGroups` |
| Collector job count (API Refresh) | TrendForge registry pins — **not** this bar |

Test: `tests/catalog_registry_merge.test.js` fails if any registry key lacks a
catalog card.

---

## 17. Feed card **data** path (Path A vs Path B)

Catalog cards and drawers read **static** fields on each inventory item. They
are **not** rewritten by `LivePanelsController`. Live overlay only mutates a
**clone** used by Sector / Consensus / Screener panels.

### Two independent sample paths

```text
PATH A — CATALOG CARD / DRAWER (“Showing N feeds” grid)
  Option 1 (legacy strong feeds):
    Excel + VERIFY_*_WITH_SAMPLES.csv + raw dumps
      → generate_json.py → links_105.json.records_sample

  Option 2 (registry expansion — preferred after MD69 collect):
    merge_registry_into_catalog.py   → card stub (may be sample-empty)
    POST /api/market-data/refresh    → market_data_latest + objects/
    fill_catalog_samples_from_collector.py
      → copies last-good records into records_sample (≤250)
      → STRONG + CONNECTED_FRESH_STRUCTURED
      → app.js / schemas.js show tables like older feeds

PATH B — LIVE PANELS only (Sector / Consensus / Screener)
  Refresh → objects/manifest → live_panels inventoryOverlay
    → live_panels.js buildPanelInventory (clone only)
  Does NOT update catalog #main-container inventory.
```

### Code ownership

| Concern | File |
|---------|------|
| Bake samples (legacy) | `generate_json.py` |
| Card stubs for new registry keys | `merge_registry_into_catalog.py` |
| Fill samples from collector last-good | **`fill_catalog_samples_from_collector.py`** |
| Card grid + count bar | `app.js` |
| Schema tables | `schemas.js` |
| Collect + store | `market_data_service.py` / `market_data_scheduler.py` |
| Overlay | `live_panels.py` + `live_panels.js` |

### Verified state after 30-pack fill (2026-08-06)

| Check | Result |
|-------|--------|
| Registry pin | **104** |
| Catalog rows | **141** |
| Collapsed primaries | ~**98** |
| Registry-merged rows sample-filled | **29** via `fill_catalog_samples_from_collector.py` |
| Awaiting sample | **0** |

Full add-link steps: **§15** above.

## 18. Pack-2 collector boundary (2026-08-10)

TrendForge now owns 104 hash-pinned collector contracts. Three new context
objects exist upstream: TradingEconomics BDI (third-party index context), Yahoo
BDRY (shipping ETF proxy, never BDI), and Google Trends India RSS (current top
topics, never keyword history). The Inventory SPA still reads its unchanged
catalog. Bringing these objects into cards or panels requires a separately
approved catalog/panel mapping and must not create votes or score terms.

The verified BDI parser v1.1 record includes value, previous value, absolute
daily change and percentage change. This remains market-regime context only.

## 19. Pack-3 catalog projection (2026-08-10)

TrendForge now owns 108 dynamic contracts. Inventory has 150 rows / 114 logical
keys and displays compact stored samples for CRISIL, ICRA, CARE and Google News
RSS. Google News row 150 contains 4 articles that survived the upstream
seven-day age gate. The SPA never fetches Google, CARE, ICRA or CRISIL itself;
it reads the catalog projection only. All four sources are informational,
unmapped by default and excluded from Consensus and Screener scores.

## 20. FII-related stock-name strip (2026-08-11)

The SPA calls the local TrendForge read-only endpoint
`/api/institutional/fii-stock-signals` through
`fii_stock_signals_panel.js`. The dedicated sibling panel is mounted directly
after `consensus-strip`, so it appears below the Nifty Filter without modifying
`consensus.js`. It renders large-deal symbols and explicit quarterly FII/FPI
holding changes as separate groups, validates symbols, escapes all text and
fails closed when the API is unavailable. It never votes or scores.

Third-party Screener/Tickertape/Dhan/Equitymaster screens are collected by
Refresh (last-good 2026-08-13: 105 / 300 / 32 / 25 rows). The inventory FII
API loads all four as zero-score INFO: Tickertape/Dhan keep ticker/ISIN;
Screener/Equitymaster use exact official-universe name mapping or stay
`NAME ONLY`. Dhan missing hold % is null, never 0.0. Must not be shown as
“FII bought today.” Official daily FII files remain market totals.

The TrendForge command room (`D:\TrendForge\frontend`) does **not** yet call
this API. That is `TF-APP-FII-M1`.

## 18. FII panel Refresh connection (2026-08-11)

The FII stock-name panel is not a separate download plane. Manual Refresh
commits registry data in TrendForge, the FII API reads those hash-verified
canonical latest objects, and the frontend completion hook repaints it beside
Sector, Consensus/Nifty Filter and Screener. The displayed time is the saved
source fetch time. FII signals remain informational and do not alter scoring.

## 19. Verified four-card FII path (2026-08-13)

`run-source` uses the existing 123-key registry, resolver, parser, hashed object
store and `market_data_latest`. `fill_catalog_samples_from_collector.py` copies
only validated last-good rows into cards 162-165; `app.js` requests
`links_105.json` with `cache: no-store` so a reload shows the new card samples.
The FII API reads the same canonical objects and performs ISIN/ticker or exact
unique-name resolution. Unresolved company names remain visible as `NAME ONLY`;
nothing is silently dropped or assigned a guessed ticker.


## Source Operations overlay - 2026-08-15

The SPA has a read-only operational panel below the five KPI cards. TrendForge
opens the same bundled runtime at `/inventory-workbench/?embed=terminal`; the
browser still does not fetch NSE/BSE directly and catalog samples are not treated
as evidence.

The panel joins compiler contracts, monitored runtime keys, fetch attempts,
parser outputs, and freshness status into six stages: compiler contracts,
monitored keys, input observed, parsed records, current facts, and facts usable
for research. Each source has `HEALTHY`, `VALID_EMPTY`, `STALE_PARTIAL`,
`BLOCKED`, `FAILED`, or `NOT_ATTEMPTED`, with reason and proof/data date.
It cannot score, rank, activate, authorize `CONFIRMED`, calculate quantity, or
execute orders. `embed=terminal` adds only the scoped `inventory-embedded`
class; the standalone layout remains unchanged.


## Hash-pin caveat - 2026-08-15

The source and bundled runtime files contain aligned feature markers but are separate revisions and are not byte-identical for this
change, but the existing snapshot manifest still contains the pre-Source-
Operations byte sizes and hashes. The existing `inventory-workbench.test.js`
also still expects the old drawer URL without `embed=terminal`. Its current
observed result is **FAIL: Size mismatch: index.html**. This means the runtime
panel observation is valid, but the manifest/test pin must be refreshed before
claiming a clean snapshot-integrity verdict. No source data, catalog sample, or
TrendForge state authority is affected by this metadata/test discrepancy.

## Post-commit cash pipeline overlay - 2026-08-15

The embedded workbench now reads one TrendForge endpoint, /api/source-operations/snapshot. The source track reports compiler, runtime, attempts, parsed records, current facts, last-good keys and research usable facts. The cash track reports the existing A1, A2, A3, A4, A5, A6, C0, B and C1 stages after a real cash-relevant last-good commit.

The panel is read-only observability. It does not fetch NSE/BSE directly, use catalog samples as evidence, score sources, activate sources, authorize CONFIRMED, calculate quantity or place orders. No cash track is displayed before a qualifying last-good commit; the UI explains that HTTP 200 alone is insufficient.

The source and bundled runtime syntax checks pass. The separate integrity manifest still needs a post-change byte/hash refresh; that metadata issue is not evidence that the operational endpoint or parser is broken.
