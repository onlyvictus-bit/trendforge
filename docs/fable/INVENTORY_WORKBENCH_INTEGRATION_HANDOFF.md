# Inventory Workbench ↔ TrendForge — Integration Plan (corrected)

**Status:** Same-origin workbench + Source Operations snapshot + cash A1–C1 post-commit are implemented. Remaining adapter/state work still follows File A.
**Updated:** 2026-08-16 (docs + overlay re-pin; collector 123 / catalog 165 / 129 keys)
**Inventory app:** `D:\trendforge_inventory_app` — **formula/scoring freeze** (do not edit `screener.js` / `consensus.js` / score policy). Catalog samples, fill script, and Source Operations glass may be updated as declared overlay files.

This file **supersedes** the older 2026-08-04 M0–M5 narrative where it conflicts (that date is the *replaced* plan, not a later revision).  
**Build selectors remain File A `R0–R18` / `CROSS-*` / `TDG-GAP-*` only.**  
Former **M0–M5** labels below are **seam tags**, not work selectors.

---

## Implementation record - 2026-08-16

- TrendForge-owned copy: `frontend/inventory-workbench/`.
- Manifest: `frontend/inventory-workbench/inventory-workbench.manifest.json`
  is a **declared overlay** (not a claim that the source app is untouched).
  Scoring engines remain frozen; catalog samples, Source Operations glass,
  cache token and fill script are overlay files.
- Serving route: `/inventory-workbench/?embed=terminal` through the existing
  FastAPI static mount; no second localhost server is required.
- Host integration: `frontend/index.html` exposes the Inventory control and
  iframe drawer; `frontend/theme-final.css` owns only its presentation.
  Desktop is `top:2vh`, `95vw` by `96vh`; `<=760px` is `100vw` by `100dvh`.
- Existing `/api/panels/live`, `/api/market-data/refresh` and
  `/api/institutional/fii-stock-signals` remain the live/saved overlays.
- Source Operations reads **one** API: `GET /api/source-operations/snapshot`.
- Cash A1–C1 is implemented and may run after a cash-relevant last-good.
  That does not activate sources or emit CONFIRMED.
- Ranking-adapter and File A live DTO work remain governed by R0–R18.

## 0. Trading architecture (reason first — then build)

A professional research scanner is a **pipeline of cheaper truth before expensive opinion**. Mixing them is how retail tools lie.

| Layer | Trading job | Honest output | Typical lie if mixed |
|-------|-------------|----------------|----------------------|
| **Collect** | Official/usable facts land once, PIT | Raw + parse + timestamp | Second downloader, sample as live |
| **Qualify** | Identity, lot, ban, freshness, empty vs fail | Usable / empty / blocked | Gate PASS = activated |
| **Discover** | Where to look first (attention) | Ordinal rank, WATCH | Rank = “best trade” |
| **Structure** | Closed-bar path | Direction eligibility | Intrabar confirm |
| **Context** | Sector, event, options package | SUPPORT/WEAKEN/CONFLICT/UNKNOWN | OI = smart money |
| **State** | One readiness vocabulary | WATCH/WAIT/CONFIRMED/REJECT | Combined_Score / HOT |
| **Geometry** | Research entry/invalidation | qty=0 | Order ticket |

**Why inventory and TrendForge must stay split**

- **Inventory SPA** is a **glass + attention workbench**: all links visible, samples, local A-score / consensus / live panels. That is **discovery UX**, not the exchange of record.  
- **TrendForge** is the **exchange-of-record stack**: fetch, immutable raw, parsers, PIT, gates, public state.  
- In markets, **attention ≠ confirmation**. Volume/RS/A-score can order a book; they cannot certify a setup. Options/OI cannot name buyer vs seller.  
- Therefore: **reuse inventory as a frozen ranking adapter**; **never** let it write `CONFIRMED`, qty, or gates.

**Why not jump to options / R12**

Options Greeks, PCR, max pain and GEX are **downstream model/context**. Without honest universe, closed structure and fail-closed IV they become theater. File A already sequences **R0 honesty → R1 claims → R2 cheap live path** before deep derivatives.

**Why not treat every catalog card as evidence**

A catalog is a **library**. Cards include PRIMARY, COMPANION, PROVENANCE, SUPPORTING, THIRD_PARTY, CONTEXT_NEWS. Companion samples can show **another venue’s fields** (observed: NSE Regulation 31 companion cards carry BSE-style `scripCode` pledge samples). Counting those as independent NSE evidence is **double-count / wrong-root**.

---

## 1. Live counts (do not freeze “105”)

Recompute before any pin. Current observed catalog/registry (do **not** freeze the filename “105”):

| Surface | Observed |
|---------|----------|
| Inventory `links_105.json` | **165 cards** |
| Unique `active_source_keys` | **129** (split compound `a\|b` keys; unsplit list entries = 122) |
| Unique primary rows | **105** (collapsed unique primaries — not 165 cards and not 129 keys) |
| TrendForge collector registry | **123** contracts (`config/source_refresh_registry_69.csv`) |
| File A CROSS-002 living map (pinned 2026-07-23) | 129-key union / 118 named + 74 runtime; **IMPLEMENTED at R0 governance ceiling** |
| Screener contract | `trendforge.screener.featureTable.v1.3` (`screener.js`) |
| Inventory `dist/` | **Does not exist** (static source tree) |
| Live panels API | **Already exists:** `GET /api/panels/live` — do not duplicate |

Drift after this date is expected. R0 residual may **recompute hashes/counts**; it must **not** redo CROSS-002 as a new map project.

---

## 2. Authority (not four equal files)

| Order | Path | Role |
|------:|------|------|
| 1 | Current user instruction + `AGENTS.md` | Conduct / safety |
| 2 | **File A** `docs/fable/new_merge_PLAN_2026-07-18.md` | **Sole sequence**: R0–R18, states, activation, qty, acceptance |
| 3 | **FINAL_MERGE** `docs/fable/FINAL_MERGE_PLAN.md` | Mandatory **mapped** FMR detail (aliases only) |
| 4 | Hybrid File B | Formulas / inventory depth when File A §0.5/§25 points |
| 5 | Discovery + Options (+ Math) | Detail catalogs; Options §18 playbook; never M-order |
| 6 | `docs/DECISIONS.md` | Lasting decisions |
| 7 | Runtime + `BUILD_STATUS.md` + `VALIDATION.md` | Evidence, not authority |
| 8 | **This handoff** | Inventory↔TF **seams only** |

**Conflict:** File A wins on order, public state, activation, quantity, execution, evidence permission, ceilings. Apply stricter safety if owner is unclear.

**Work selectors:** `R0–R18`, `CROSS-*`, `TDG-GAP-*` only. Never `M0–M5` / Discovery `M/T/PK`.

---

## 3. Freeze inventory (read-only)

**Path:** `D:\trendforge_inventory_app`  
**Do not edit** formulas or product UI (`screener.js`, `consensus.js`, `app.js` scoring/panels) for this plan.

**Hash-pin before adapter work** (store hashes in BUILD_STATUS / VALIDATION):

- `links_105.json`
- `screener.js` (v1.3 featureTable)
- `consensus.js`
- `schemas.js`
- relevant golden tests (`tests/screener_extractors.test.js`, `tests/screener_financial_golden.test.js`)

**What the frozen app may show (already):** catalog, local screener, consensus, live panels, FII panel.  
**What it cannot show without a later approved client change:** new File A state / entry / target / why_not_confirmed contracts.

**New decision outputs** go to the **existing TrendForge frontend** first.

**Frontend chrome (seam only):** `docs/fable/FRONTEND_SHELL_ALIGNMENT_PLAN.md` — transplant FINAL_PRODUCT IA onto live `frontend/*`. Not File A R15. Not a second downloader. Does not edit this inventory app.

---

## 4. Observed constraints (do not re-learn the hard way)

1. `require("./screener.js")` → `ReferenceError: window is not defined`. Headless use needs a **Node VM / browser shim** (as existing inventory tests already do).  
2. Bundle must be built from **TrendForge parsed PIT**, not catalog `sample_row`.  
3. Eligibility per row: `EVIDENCE` | `VALID_EMPTY` | `CATALOG_ONLY` (companions/provenance/static samples ≠ independent evidence).  
4. Existing `GET /api/panels/live` is the live-panel bridge — **no second bridge**.  
5. Same-origin cutover is **implemented** at `frontend/inventory-workbench/` as an allow-listed, hash-verified static snapshot; it is not a new downloader or authority plane.
6. Ordinary scanner `qty=0`. File A §25.23 VRP research lot is a **narrow future inspector exception** after R12+R16+R18 only.

---

## 5. Correct build order (File A)

```text
R0 residuals (NOT a new CROSS-002)
  scoring-engine freeze + declared overlay (done 2026-08-16)
  → R1 live DTO / radar / missing-evidence / lineage
     inventory-source-bundle.v1 from last-good + aliases + cadence clocks
     NOT a rebuild of cash A1–C1
  → R2 attention order over existing A1–C1
     inventory discovery = SHADOW only (CROSS-004 / TDG-GAP-014)
     public_state ∈ {WATCH, WAIT, REJECT}
  → separately approved UI ticket to *display* those DTOs
     (workbench / Source Operations is NOT that page today)
  → R3–R18 in File A sequence (no jump to R12)
```

There is **no extra adapter milestone**. Inventory reuse is owned only as File A residuals:

| Adapter piece | File A owner |
|---------------|--------------|
| Hash-pin `links_105.json`, `screener.js` v1.3, `consensus.js`, `schemas.js`, goldens | **R0** residual |
| `inventory-source-bundle.v1` from TF PIT + lineage | **R1** / **CROSS-019** / **TDG-GAP-004** |
| Discovery rank + ≥3 shadow runs via Node VM shim | **R2** / **CROSS-004** / **TDG-GAP-014** |

### 5.1 Finish actual **R0** residuals

**Do not repeat CROSS-002.** It is complete at the **governance ceiling** (living map reviewed; `sourceGovernanceReady` independent of `sourceActivationReady=false`).

Still open (coverage):

| Residual | Typical IDs |
|----------|-------------|
| Scoring-engine freeze + declared overlay re-pin (165/129/123/105) | **Done 2026-08-16** (R0 residual) |
| Source-specific extended fields | TDG-GAP-001, Hybrid §15.3 |
| Maturity transition history | CROSS-006, TDG-GAP-011 |
| Mirror / resolver / dataset-root authority | CROSS-007, TDG-GAP-024 |
| Workbook/count/hash recompute after catalog growth | HYBRID-2-1 / HYBRID-16-1 |
| No silent activation; no CONFIRMED from inventory | File A §9.4 / §10.4 |

**Trading reason:** a 165-card library without per-source clocks, mirrors and authority caps will **rank garbage with the same confidence as bhavcopy**.

### 5.2 Complete **R1** live DTO (not A1–C1, not the workbench)

Cash A1–C1 is already implemented. R1 builds the **live evidence object**.

- One row per **126 registry jobs**, alias-aware (catalog family aliases share a parent job)
- Eligibility: `EVIDENCE` | `VALID_EMPTY` | `CATALOG_ONLY`
- Envelope / HTTP 200 / junk / stale last-good ≠ EVIDENCE
- Cadence-aware clocks (Friday EOD can be current on Sunday)
- `missing_evidence` / `why_not_confirmed`
- `evidence_strength` labelled **“Evidence strength - not win probability”**
- `inventory-source-bundle.v1` from last-good + parsers + PIT (`evidenceAsOf`, SHA-256)
- Live radar from this DTO — current `/api/radar` is **not** R1

**Not on the new UI page.** Source Operations last-good / HEALTHY counts are collector health, not stock evidence.

**Trading reason:** if the object a human sees cannot say *why not confirmed*, every rank looks like a tip.

### 5.3 Inventory adapter pieces (owned by R0 / R1 / R2 — not a fifth milestone)

Build **in TrendForge only**. Split by File A owner (table in §5). Do not open an unofficial “adapter” work packet.

| Artifact | Rule |
|----------|------|
| `trendforge.inventory-source-bundle.v1` | From TF PIT/parsers; `evidenceAsOf`; SHA-256; unique source contracts |
| Eligibility | EVIDENCE / VALID_EMPTY / CATALOG_ONLY — companions never independent NSE votes |
| Engine | Frozen `screener.js` **v1.3** via **Node VM shim** (hash-pinned); policy `trendforge.screener.a-only.v1` |
| `trendforge.inventory-discovery.v1` | `authority=DISCOVERY_QUEUE_ONLY`; ≤500; no B/C as votes; no state/qty |

Prove **≥3 deterministic** shadow runs. Selector modes (later, config only): `BASELINE | SHADOW | PRIMARY`. Default remains TF baseline until R2 acceptance.

Do **not** port screener formulas to Python. Do **not** edit frozen scoring engines (`screener.js`, `consensus.js`, `schemas.js`). Declared overlay glass files are already governed separately.

### 5.3a Already wired (not next work)

These seams are implemented and must not be rebuilt as a new milestone:

- Cash A1–C1 modules + post-commit after last-good
- `GET /api/source-operations/snapshot` (source track + cash track)
- MD69 Refresh / scheduler on the 126-contract registry
- Inventory workbench same-origin drawer

Remaining File A work is **R1 live DTO → R2 attention order**. Do not rebuild A1–C1.

### 5.4 Complete **R2** (attention order, not a new S0–S3)

Use the **existing** cash A1–C1 states as the spine. Inventory A-score is **shadow attention only**.

```text
existing A2/A3/C1  →  R2 orders that WATCH/WAIT/REJECT queue
public_state ∈ {WATCH, WAIT, REJECT}
BASELINE = TrendForge C1 until shadow runs pass
```

- ≥3 deterministic shadow runs via Node VM + frozen v1.3
- Family router: cash/index only into cash A1–C1
- 126 jobs; catalog aliases and companions never extra votes
- R2-B named activation remains **closed**

**Not on the new UI page.** The workbench Refresh / Consensus / Screener / Source Operations panels do **not** display R2 attention rank.

No early CONFIRMED. If `sourceActivationReady=false` → research WAIT.

**Trading reason:** cheap full-universe attention is how desks scan; expensive chain/Greeks stay shortlist-only (later R12).

### 5.5 Then File A sequentially (R3–R15 debug, 2026-08-16)

Do **not** jump to options or Scanner Lab because the catalog page looks complete.

`resolve_evidence`, `analyze_closed_bar_structure`, `evaluate_option_chain` and
`evaluate_mcx_contract` are **fixture-strong** today. They are not called from
cash post-commit or from the workbench. Live R3 must consume the **R1 DTO**,
not catalog samples.

R1/R2 are live. **R3 is locked in** `R0_R1_R2_LOCKED_PLAN` **§13 including §13.9** — exact-lineage adapter +
`resolve_evidence` + WAIT diagnostics; R3 does **not** write `public_state`.
Then R4 IDs → R14 CA join before any live R5 CONFIRMED → R6 (extend A6) → R8
(not `screener.js`) → R9 verified bars → R10 pipes → R11 MCX WAIT → R12
option last-good → R13 → **R15 Scanner Lab on the TrendForge frontend**.
Workbench is never R15. Do not re-plan R3 at build time.

### 5.6 Frontend — workbench is not R1/R2

| Now | Later (separate approval) |
|-----|---------------------------|
| Workbench + Source Operations = **collector / cash-stage glass only** | A new or extended page that **reads** R1 DTO + R2 queue |
| Catalog samples and last-good lamps | Must not be painted as live stock evidence or rank |
| Reuse `GET /api/panels/live` and `GET /api/source-operations/snapshot` | No second live-panel or second ranker |
| Frozen scoring engines | Do not display inventory A-score as File A state |

**Locked:** R1 live stock evidence and R2 ranking **are not connected** to the new UI integration page. Build the TrendForge objects first. Wire the page only after those contracts exist and a display ticket is approved.

---

## 6. Contracts (still valid — counts not hardcoded)

### A) `trendforge.inventory-source-bundle.v1` (TF → engine)

- `bundleId`, `generatedAt`, `evidenceAsOf`, `payloadSha256`
- Rows from **parser outputs**, not catalog samples
- Eligibility: `EVIDENCE` | `VALID_EMPTY` | `CATALOG_ONLY`
- `VALID_EMPTY` → 0 scored rows; stale/failed/blocked/future → catalog only
- Fetch unique **source contracts**, not mirror storms

### B) `trendforge.inventory-discovery.v1` (engine → TF)

- Input bundle hash; engine `trendforge.screener.featureTable.v1.3`; policy `a-only.v1`
- `authority=DISCOVERY_QUEUE_ONLY`; max 500; finite scores; unique symbols; deterministic ties
- **No** consensus votes, win%, public state, quantity

### C) Existing APIs (reuse)

- `GET /api/panels/live` — live-panel snapshot (already implemented)
- `POST /api/market-data/refresh` — localhost MD69 collector (126 jobs)
- `GET /api/source-operations/snapshot` — collector + cash-stage lamps; **not** R1 DTO / R2 rank
- Do not invent a parallel refresh/panel/rank stack

### D) UI disconnect (locked)

R1 bundle and R2 attention queue are TrendForge objects. The new workbench
page does not consume them. A later display ticket may bind them. Until then
catalog samples and Source Operations counts are not live stock evidence.

---

## 7. Code seams (TrendForge only until UI approval)

**Expected TF files (create/extend as R\* work):**  
`inventory_source_bundle.py`, PIT selectors, `inventory_discovery.py` + **VM runner**, thin scanner selector, tests under `backend/tests`

**Inventory:** **no edits**. Runner lives in TF and **reads** hash-pinned files.

**Do not edit:** `consensus.js` voting; A-only policy id without approval; TF CORS list; `/api/radar` as new decision truth.

---

## 8. Tests / judge

```powershell
# Frozen inventory (syntax/goldens only — do not “fix” by editing)
cd D:\trendforge_inventory_app
node --check screener.js
node --check consensus.js
node tests/screener_extractors.test.js
node tests/screener_financial_golden.test.js

# TrendForge
cd D:\TrendForge\backend
# use project venv / PYTHONPATH as documented
python -m pytest -q --tb=no
```

**REFUTED if:** future/stale evidence scores; score→state; browser↔exchange; silent fallback; CORS widened; companion counted as independent official evidence; CROSS-002 rebuilt as a new spine; M-ids used as work selectors.

---

## 9. One-line law

**Inventory is frozen scoring glass plus declared overlay.**  
**TrendForge is the only data, gate and state authority.**  
**Cash A1–C1 is done. Build R1 live DTO → R2 attention order. Do not connect them to the workbench until a display ticket exists.**

---

**Canonical path:** `D:\TrendForge\docs\fable\INVENTORY_WORKBENCH_INTEGRATION_HANDOFF.md`  
**Inventory mirror:** stale 2026-08-04 pointer file — **do not edit inventory**; trust this TrendForge path.


## Source Operations panel - 2026-08-15 (corrected 2026-08-16)

The Inventory button now opens the bundled workbench inside the
TrendForge drawer at `/inventory-workbench/?embed=terminal`. A second downloader
or a second health engine was not created.

Purpose: show whether each source flow is observed, parsed, current, usable for
research, stale, blocked, failed, or not attempted. The panel reads **one**
API: `GET /api/source-operations/snapshot`. That snapshot already joins
compiler, catalog, fetch attempts, parser outputs, freshness and last-good
(with normalized-key aliases). It renders the six-stage path:
`compiler contracts -> monitored keys -> input observed -> parsed records ->
current facts -> facts usable for research`.

Each source has a typed state: `HEALTHY`, `VALID_EMPTY`, `STALE_PARTIAL`,
`BLOCKED`, `FAILED`, or `NOT_ATTEMPTED`. Valid empty is different from failure.
Metadata-only, malformed, stale, blocked, and unattempted data stay explicit.
The panel shows `Shared HTTP / breaker unspecified` when source-specific proof
is not available; it makes no automatic-retry claim.

This is operational evidence only. It cannot rank a stock, count correlated
cards as separate votes, activate sources, authorize `CONFIRMED`, calculate
quantity, place orders, or change TrendForge state authority. `sourceActivationReady`
and `gateAuthorized` remain separate values.

The `embed=terminal` query applies the scoped `inventory-embedded` class for a
compact drawer layout only. Standalone inventory rendering remains unchanged.
Scoring engines stay frozen. Overlay files (catalog samples, Source Operations
glass, cache token) are re-pinned in the workbench manifest.

Observed verification on 2026-08-15: the drawer loaded the panel immediately
below the KPI cards; the stale filter opened 50 named source rows. The observed
run showed 354 compiler contracts, 132 monitored keys, 56 input-observed
sources, 47 parsed-record sources, 5 current facts and 5 facts usable for
research; status counts were 5 healthy, 1 valid-empty, 50 stale/partial,
0 blocked, 0 failed and 76 not-attempted. After alias last-good matching
(2026-08-16) last-good resolved count is **97** (93 exact + 4 alias). These are
run observations, not frozen inventory totals.


## Hash-pin / overlay - 2026-08-16

Chosen mode: **declared TrendForge overlay**, not a pretence that the source
app is byte-identical. `inventory-workbench.manifest.json` is re-pinned.
`inventory-workbench.test.js` accepts `/inventory-workbench/?embed=terminal`
and overlay-listed files. Scoring/formula files must still match the frozen
source hashes. This is snapshot integrity, not state authority.

## Post-commit bridge status - 2026-08-15

The embedded workbench now reads one Source Operations snapshot containing two
tracks: source acquisition/lineage and the existing cash A1-C1 post-commit
status. Refresh and Scheduler trigger the bridge only after a schema-valid
cash-relevant last-good commit. The workbench remains read-only glass; it does
not run collectors, call A1-C1, activate sources, create CONFIRMED, calculate
quantity or place orders. The live cash track now has a verified completed run; later missing artifacts remain explicit rather than inferred.


## Cadence-aware source dates, family dispatch and scheduler closure - 2026-08-16

### Observed evidence

The manual registry run `2026-08-16-manual-20260816-123159-0047999505c9` attempted all **123** source contracts. The result was re-audited from normalized object contents, not HTTP status or manifest row count:

| Result class | Sources | Meaning |
|---|---:|---|
| Usable parsed records | 107 | Normalized market, event, holdings, contract or macro rows were present. This is data readiness evidence only, not activation or confirmation authority. |
| Valid empty | 3 | Empty was explicit and remains different from fetch/parse failure; it supplies no candidate rows. |
| Stale last-good fallback | 3 | Prior rows were retained after current transport/parser failure; they are visible but non-current. |
| Status/schema envelope only | 10 | Collector returned a normalized status envelope rather than usable trading records; HTTP/collector success must not count these as usable data. |

The cadence registry currently contains 32 intraday, 28 daily EOD, 15 daily/change-detect, 12 event-driven, 11 slow event-driven, 11 weekly, 5 quarterly, 3 intraday-event, 2 commodity EOD, 2 fortnightly and 2 session-window contracts. Its cadence evidence is still predominantly `PROVISIONAL_UNVERIFIED_NEEDS_OFFICIAL_WEB_CHECK`; the audit therefore records provisional disposition rather than activation truth.

The cadence-aware audit identifies **8** late or suspect contracts and **4** usable sources that still lack temporal proof. It does not call every old date stale. Examples:

- `nse_bhavcopy_eod` and `nse_fo_bhavcopy` dated 2026-08-14 are current for the latest NSE session when run on Sunday 2026-08-16.
- CFTC reports dated 2026-08-11 and EIA weekly petroleum data dated 2026-08-07 are plausible current weekly publications, pending official cadence proof.
- Event-driven disclosure dates describe the latest event, not collector freshness by themselves.
- `nsdl_fpi_daily_reportdetail` dated 2024-08-23 and `cdsl_fpi_fortnightly` dated 2024-08-26 are suspect parameter/publication selections and cannot be called current.
- `mcx_bhavcopy` remains an explicit stale last-good fallback. `bse_financial_results_xbrl` and `bse_shareholding_pattern` were subsequently repaired with populated data dated 2026-08-15; the historical statement above is retained only as the pre-repair observation.

The validated pending workbook `data/reports/SOURCE_LINK_INVENTORY_MASTER.updated.xlsx` contains `CADENCE_SUMMARY` and `CADENCE_AUDIT` sheets with URL, cadence, observed/derived data date, actual parsed-row count, usability class, dispatch rule and required next action for every registry source. Replacing the canonical workbook is awaiting separate explicit approval.

### Workbench integration consequence

The Inventory Workbench Refresh button remains a client of TrendForge `POST /api/market-data/refresh`; it does not download market sites itself. On completion it may repaint live panels and Source Operations. The backend must expose cadence-aware source states and family-dispatch outcomes. It must not imply that every source entered cash A1-C1 or that a status envelope is usable data.

Snapshot handling chose **declared overlay** and re-pinned the workbench
manifest. Scoring engines stay frozen. Refresh downloads **123** registry jobs,
which cover the **129** inventory keys through six aliases. Companion cards are
not extra fetches. `run_server.py` defaults the two MD69 flags so Refresh is
not 503. HTTP 200 / junk HTML / empty / stale is not usable. A1–C1 may run
after a cash-relevant last-good only.



## Verified refresh-to-workbench connection - 2026-08-16

The drawer is connected, but it is intentionally **not** a downloader. Its Refresh button calls the same local API as the main terminal: `POST /api/market-data/refresh`. The API starts one 126-contract registry job; `GET /api/market-data/refresh/status` reports progress; `GET /api/source-operations/snapshot` repaints the read-only source and cash tracks after completion. The 165 cards are catalog views, not 165 fetch requests; catalog aliases/companions do not become independent downloads or votes. `links_105.json` is a legacy filename.

Automatic collection is now wired into normal local API startup: `run_server.py` / `scripts/start_api_md69.ps1` enable `MARKET_DATA_69_AUTOSTART=1`, and `main.py` creates one lifecycle-managed 15-second foreground scheduler. It must not run beside `start_md69_scheduler.ps1`; Windows logon persistence is still outside this claim.

The calendar-aware post-commit repair is live. The scheduler derives the latest expected NSE EOD before A1-C1, so a Sunday run correctly uses Friday 2026-08-14. Unknown calendar, malformed data, stale data or metadata-only data cannot enter the cash path. The verified live Refresh completed 123 contracts (119 new, 1 retained last-good, 3 valid-empty, zero failures), dispatched A1/A2/A3/A4/A6/C1, and kept A5 and B explicit skips. The resulting 2,463 C1 rows remain research-only: `sourceActivationReady=false`, `canUnlockConfirmed=false`, `executable=false`, `WATCH_WAIT_REJECT`.
