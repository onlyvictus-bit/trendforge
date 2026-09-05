# TrendForge Inventory App — Graphs & Diagrams

## Current official-source and calculation flow (2026-08-11)

```mermaid
flowchart LR
  BSEF["BSE financial filing index"] --> C["TrendForge collector and last-good store"]
  BSES["BSE shareholding filing index"] --> C
  RBI["RBI T-bill auction yields"] --> C
  NSEI["NSE Nifty 500 industries"] --> C
  NSEO["NSE equity option chain"] --> C
  C --> J["links_105.json: 165 cards / 129 logical keys"] --> UI["Inventory SPA"]
  C --> PEER["industry_peer_group_v1: 500"]
  C --> GREEKS["option_greeks_calculated_v1: 65"]
  C --> PCR["pcr_max_pain_history_v1: 1 observed date"]
  C --> RATIOS["fundamental_ratios_v1: WAIT for numeric iXBRL facts"]
  PEER -. "zero-score; no source count" .-> UI
  GREEKS -. "zero-score; no source count" .-> UI
  PCR -. "zero-score; no source count" .-> UI
```

The source registry count is **119**. Calculated keys are content-addressed
research objects only; they do not inflate that count or enter Consensus and
Screener formula registries.

## Files 1-7 recovery flow (historical checkpoint, 2026-08-11)

```mermaid
flowchart LR
  A["Anonymous official or approved free sources"] --> C["Existing TrendForge collector"]
  U["UPSTOX_ANALYTICS_TOKEN"] --> R["15 GET-only read-only contracts"] --> C
  C --> V["Validate and normalize"] --> S["Existing raw archive and last-good store"]
  S --> J["historical checkpoint: 158 cards / 122 keys"] --> P["Inventory and three research panels"]
  S --> I["Observed ATM IV by session"] --> G{"252 distinct sessions?"}
  G -- "No" --> W["WAIT_INSUFFICIENT_HISTORY"]
  G -- "Yes" --> D["Derived informational IV rank"]
  P -. "zero-score support only" .-> D
```

The exact 77-row state map is
`D:\TrendForge\docs\fable\evidence\FREE_SOURCE_RECOVERY_77_MATRIX_20260811.csv`.

## Packs 6-7 option flow (historical checkpoint, 2026-08-11)

```text
Official NSE option endpoint -> TrendForge resolver/archive -> parser v1.1
                                                              |-> identity gate
                                                              |-> Max Pain from OI
                                                              `-> saved overlay -> SPA

Upstox read-only route --------------------------------------> TOKEN REQUIRED
Other credentialed broker/UI routes ------------------------> REPLACED / BLOCKED
Synthetic Greeks/mock predictions ---------------------------> REJECTED
```

## Pack 5 flow (2026-08-11)

```text
NSE marketStatus -----> official session context ----+
NSE PIT(symbol fanout) -> BUY/SELL disclosure support +-> TrendForge archive/store
RupeeVest bundle ------> monthly MF-flow support -----+          |
                                                              catalog sample
                                                                   |
                                                        Inventory cards only
```

All three branches are zero-score. Consensus and Screener formula paths are
unchanged.

## Manual and scheduled entry paths

```mermaid
flowchart LR
  T["Six IST checkpoints"] --> L["Existing MD69 lease"]
  B["Refresh button"] --> A["Local refresh API"] --> L
  R["Dynamic source registry"] --> L
  L --> C["Existing collector and validators"] --> S["Committed last-good files and manifest"]
  C -. "failure or valid-empty" .-> S
  S --> P["Hash-verified canonical projection"] --> U["Sector / Consensus / Screener"]
```

The saved object carries its original source date and fetch timestamp. It may
render as research data, but only fresh panel-critical sources can make the
panel green `LIVE`. See the [operation reference](../TrendForge/docs/fable/MD69_REFRESH_OPERATION_REFERENCE.md)
for source add/remove and state flows.

## MD69 canonical collection path — collector path and activation status

```mermaid
flowchart LR
  R["69-key hash-pinned registry"] --> S["IST due scheduler and SQLite lease"]
  S --> A["Existing endpoint or resolver adapters"]
  A --> V["Validate and normalize"]
  V --> O["SHA-256 object store and last-good"]
  O --> M["69-entry manifest and health"]
  M --> T["Timestamp alignment"]
  T --> P["Cloned read-only panel overlay"]
  P --> UI["Sector / Consensus / Screener panels"]
  K["User-approved PROVISIONAL override"] --> S
```

The SPA remains a display/catalog consumer. It does not fetch market sources or
own the scheduler. The named Windows scheduled task was not found during the
2026-08-06 audit, so automatic execution is not claimed until it is recreated
and observed.

Render these diagrams in any Mermaid-capable viewer (GitHub, VS Code Mermaid, Notion, etc.).

Related: [ARCHITECTURE.md](./ARCHITECTURE.md) · [INDEX.md](./INDEX.md) · [README.md](./README.md)

---

## 1. System context

```mermaid
flowchart TB
  subgraph Upstream["TrendForge Data Plane"]
    XLS["SOURCE_LINK_INVENTORY_MASTER.xlsx"]
    CSV["VERIFY_ALL_112_WITH_SAMPLES.csv"]
    RAW["Raw endpoint dumps"]
  end

  GEN["generate_json.py"]
  JSON["links_105.json\n112 rows · 76 unique keys"]

  subgraph Browser["Static SPA"]
    HTML["index.html"]
    APP["app.js"]
    SCH["schemas.js"]
    CON["consensus.js v4"]
    PLG["consensus_plugins.js"]
  end

  USER["Operator / Researcher"]

  XLS --> GEN
  CSV --> GEN
  RAW --> GEN
  GEN --> JSON
  JSON --> APP
  HTML --> APP
  SCH --> APP
  CON --> APP
  PLG --> CON
  APP --> USER
  CON --> USER
```

---

## 2. End-to-end data flow

```mermaid
flowchart LR
  A[Linked source contract] --> B[Verify download]
  B --> C[Raw file on disk]
  C --> D[generate_json parse + transform]
  D --> E[complete engine records / ≤250 display samples]
  E --> F{UI path}
  F --> G[Schema table RANKED / LATEST]
  F --> H[Consensus board voter]
  H --> I[Top-5 BUY / SELL strip]
  G --> J[Drawer / CSV export]
```

---

## 3. Frontend component graph

```mermaid
flowchart TB
  index["index.html"]
  css["styles.css"]
  app["app.js"]
  schemas["schemas.js"]
  cons["consensus.js"]
  plug["consensus_plugins.js"]
  data["links_105.json"]

  index --> css
  index --> schemas
  index --> cons
  index --> plug
  index --> app
  app -->|fetch| data
  app -->|getSchemaForItem| schemas
  app -->|renderConsensusStrip| cons
  schemas -.->|flattenPreOpen| cons
  plug -->|registerConsensusBoard| cons
```

---

## 4. App runtime sequence

```mermaid
sequenceDiagram
  participant U as User
  participant H as index.html
  participant A as app.js
  participant J as links_105.json
  participant S as schemas.js
  participant C as consensus.js

  U->>H: Open localhost:8080
  H->>A: DOMContentLoaded
  A->>J: fetch inventory
  J-->>A: 112 items
  A->>A: KPIs, topics, field cloud
  A->>A: filter + render cards
  A->>C: renderConsensusStrip(inventory)
  C->>C: index + score boards
  C-->>A: strip HTML BUY/SELL
  U->>A: open card drawer
  A->>S: getSchemaForItem
  S-->>A: columns / mode
  A-->>U: table + sample JSON
  U->>C: click consensus pill
  C-->>U: breakdown modal
```

---

## 5. Consensus scoring graph

Shared pipeline for **both** UI strips (score once).

```mermaid
flowchart TB
  INV[Inventory array] --> IDX[Index by sourceKey]
  IDX --> CACHE[Source load + preprocess cache]

  subgraph Boards["Board registry"]
    M[Momentum]
    P[Preopen]
    V[Volume ±]
    D[Deals BUY/SELL]
    R[Risk ASM/GSM]
    I[Insider PIT]
  end

  CACHE --> Boards
  Boards --> TOPK["Top-K unique symbols\npoints = w × rank × quality"]
  TOPK --> AGG[Per-symbol BUY/SELL bags]
  AGG --> FAM[Family decay]
  FAM --> DOM[Dominant side + mixed edge]
  DOM --> QUAL{Qualify?}
  QUAL -->|multi-board / multi-family / strong single| RANK[Sort confidence → score]
  QUAL -->|no| DROP[Exclude]
  RANK --> FULL["buyRanked / sellRanked\nfull ordered lists"]
  FULL --> S1["Section 1: top 5 BUY/SELL\nCross-Board Consensus"]
  FULL --> S2["Section 2: ∩ Nifty set\nthen top 5 BUY/SELL"]
```

### 5b. Dual strip: Cross-Board vs Nifty filter

How stocks are **calculated, ordered, selected, shown**:

```mermaid
flowchart TB
  DATA["inventory samples"] --> SCORE["Score on all voting boards\npoints = weight × rank × quality × family_decay"]
  SCORE --> QUAL["Qualify\n≥2 boards OR strong single\ndrop pure ties / weak mixed"]
  QUAL --> SORT["Order\nconfidence → families → boards → score"]
  SORT --> LIST["RANKED LIST\nbuyRanked / sellRanked"]

  LIST --> A["SECTION 1\nCross-Board Consensus v4"]
  LIST --> B["SECTION 2\nNifty filter Trusted index"]

  A --> A1["Select: all qualified names"]
  A1 --> A2["Show: top 5 BUY + top 5 SELL"]
  A2 --> A3["Pills — may include small/thin stocks"]

  B --> B0["Nifty universe\nNifty 50 static ∪\nnse_nifty500_constituents"]
  B0 --> B1["Select: ranked name ∈ Nifty set"]
  B1 --> B2["Show: top 5 BUY + top 5 SELL"]
  B2 --> B3["Pills — large/mid index names only"]

  A3 --> CLICK["Click pill → breakdown modal\nboards + inventory links"]
  B3 --> CLICK
```

```mermaid
flowchart LR
  subgraph Same["Same for both sections"]
    C[Calculate scores]
    O[Order ranked lists]
  end
  subgraph Diff["Different only at gate"]
    S1[Section 1: no index gate]
    S2[Section 2: Nifty membership required]
  end
  C --> O --> S1
  O --> S2
```

| Step | Cross-Board Consensus v4 | Nifty filter |
|------|--------------------------|--------------|
| Calculate | Board points + family decay | **Same** (reuse ranked lists) |
| Order | confidence → boards → score | **Same** |
| Select | Score rules only | Score rules **+** ∈ Nifty 50/500 |
| Show | Top 5 BUY / SELL any symbol | Top 5 BUY / SELL after Nifty filter |

**One line:** Section 1 = best scores anywhere · Section 2 = best scores **that are also on Nifty**.

**Data for Nifty set:** static Nifty 50 in `consensus.js` + `Symbol` / `entity_list` from inventory `nse_nifty500_constituents`.

**Code files:** `consensus.js` (`computeConsensus`, `buildNiftyUniverse`, `filterToNifty`, `renderConsensusStrip`) · host `#consensus-strip` in `index.html`.

---

## 6. Consensus board families

```mermaid
mindmap
  root((Consensus v4))
    Momentum
      nse_gainers
      nse_losers
    Preopen
      gap_up
      gap_down
    Volume
      spike_up pChange&gt;0
      spike_down pChange&lt;0
    Deals
      nse_large_deals
      nse_snapshot
      bse_bulk
      bse_block
      nse_block*
    Risk
      ASM
      GSM
    Insider
      PIT buy
      PIT sell
    Plugins
      registerConsensusBoard
```

---

## 7. Inventory classification (historical 105-row snapshot)

```mermaid
pie title Inventory status (live JSON)
  "STRONG" : 68
  "PROVENANCE" : 23
  "COMPANION" : 11
  "CONTEXT_NEWS" : 3
```

```mermaid
pie title Screener integration labels
  "LINKED_RESEARCH_SCREENER" : 34
  "RESEARCH_CONTEXT_ONLY" : 30
  "GATE_DEPENDENCY" : 28
  "SCANNER_OPERATIONAL_INPUT" : 7
  "Other context" : 6
```

---

## 8. Usefulness model for stock / cross-board screening (historical audit)

**Canonical table + key lists:** [INDEX.md — Screener usefulness audit](./INDEX.md#screener-usefulness-audit-canonical)  
**Audited:** live `links_105.json` (2026-08-03). Not the same as `status=STRONG`.

### 8.1 Historical row split (105)

```mermaid
pie title Screener usefulness class (rows)
  "A classic movers (12)" : 12
  "A broader identity (4)" : 4
  "B special stock (43)" : 43
  "C options F&O MCX (11)" : 11
  "D context (35)" : 35
```

```mermaid
flowchart TB
  ALL["Historical 105-row snapshot\n69 raw source-key fields"]

  ALL --> A["A classic: 12 rows / 10 feeds\nname + LTP/%/vol/gap"]
  ALL --> AB["A broader: +4 rows\nuniverse / indices"]
  ALL --> B["B special: 43 rows / 20 primaries\ndeals · pledge · PIT · ASM/GSM · OI · SLB"]
  ALL --> C["C F&O: 11 rows / 9 primaries\nOI/vol/strike — NO greeks"]
  ALL --> D["D context: 35 rows\nmacro · FII · news · calendar"]

  A --> CB[Cross-board rails]
  B --> CB
  C --> OPT[Derivatives tables]
  D --> CTX[Research only]
  AB --> UNI[Universe / identity]

  CB --> STRIP["Consensus strip\n~13 keys wired today / 19 rows"]
```

### 8.2 Claim vs audit

| Claim | Verdict | Live |
|-------|---------|------|
| A ~12 rows / ~10 feeds | **TRUE** | 12 / 10 |
| B ~43 rows | **TRUE** | 43 |
| C ~9 (no greeks) | **TRUE** (feeds) | 11 rows / 9 primaries; greeks **0** |
| D ~38 | **≈ TRUE** | 35 |
| A+B+C ~66 useful | **≈ TRUE** | **70** rows |
| ~36 unique boards | **≈ TRUE** | **42** primaries / **48** keys |
| Option chain often empty | **TRUE** | equity+index chain `n=0` |
| STRONG ≠ stock picker | **TRUE** | STRONG=68 includes macro/commodity |

### 8.3 Simple POV (verified)

```
105 inventory link rows
 ├─ ~70  → stock/contract screener useful (A+B+C)
 │         but only ~42 unique primaries / ~48 keys
 ├─  12  → classic volume / % / gap movers (10 feeds)
 ├─  11  → options/F&O/MCX (OI/volume, NOT greeks)
 └─  35  → context / macro / news / calendar
```

### 8.4 Cross-board vs “useful”

```mermaid
flowchart LR
  U["A+B useful keys ~34+"] --> W["Wired in consensus.js\n13 keys"]
  U --> P["Plugin candidates\nmost-active · bhavcopy\nOI spurts · SLB · sector · live opt"]
  W --> S[BUY/SELL strip]
  P --> PLG[consensus_plugins.js]
  PLG --> S
```

| | Count |
|--|------:|
| Rows touching current consensus keys | **19** |
| Unique consensus keys present | **13** |
| Greeks boards | **0** |

---



## 9. Generate → browse dependency

```mermaid
flowchart LR
  subgraph Repo["trendforge_inventory_app"]
    GEN[generate_json.py]
    JSON[links_105.json]
    UI[SPA files]
    DIAG[diag_*.py]
  end

  subgraph TF["D:\\TrendForge\\data"]
    MASTER[reports / Excel]
    VERIFY[verified_downloads CSV]
    RAWP[raw_sources]
  end

  MASTER --> GEN
  VERIFY --> GEN
  RAWP --> GEN
  GEN --> JSON
  JSON --> UI
  JSON --> DIAG
```

---

## 10. Future link onboarding (engine connection required)

```mermaid
flowchart TB
  N1[New official endpoint] --> N2[Add to master Excel + verify download]
  N2 --> N3[Add TrendForge endpoint/resolver\nparser + validator]
  N3 --> N4[Update 69 CSV/YAML\nhashes/counts if registry changes]
  N4 --> N5[python generate_json.py]
  N5 --> N6[Row appears in UI catalog]
  N6 --> N7{Calculation role?}
  N7 -->|Screener field| N8[Register extractor\nadd schema if needed]
  N7 -->|Consensus vote| N9[Register approved plugin board\nprove no duplicate family vote]
  N7 -->|Live panel| N10[Add explicit overlay/critical role\nfreshness + holiday tests]
  N7 -->|Catalog only| N11[No engine connection]
  N8 --> N12[Run fixture + regression tests]
  N9 --> N12
  N10 --> N12
  N11 --> N12
  N12 --> N13[Reload browser — verify rows, date and panel state]
```

## 10A. Verified dynamic/static source linkage (2026-08-06)

```mermaid
flowchart LR
  XLS["Excel LINKED_SOURCES\n112 rows · 110 URLs\n69 raw fields · 76 logical keys"] --> GEN["generate_json.py"]
  GEN --> JSON["links_105.json"]
  JSON --> CAT["Catalog cards + drawers\ndynamic"]
  JSON --> IDX1["Consensus inventory index\ndynamic source lookup"] --> BOARDS["22 boards\n13 static source keys"]
  JSON --> IDX2["Screener inventory index\ndynamic source lookup"] --> EXT["34 static extractors"]
  IDX2 --> NIFTY["Nifty filter\nNifty universe gate"]
  REG["MD69 registry\n69 endpoint contracts"] --> LIVE["18-key live overlay allowlist"]
  LIVE --> PANELS["Sector / Consensus / Screener\ncloned panel overlay"]
  IDX3["nse_all_indices lookup\ndynamic"] --> SECTOR["Sector pulse\n38 static tracked names"]
```

Adding a catalog row changes `CAT` only. It reaches `BOARDS`, `EXT`, `LIVE` or
`SECTOR` only after the corresponding parser/adapter and explicit role
registration are added and tested. This is the reason the three panels do not
automatically consume every catalog link.

---

## 11. File responsibility matrix

```mermaid
flowchart LR
  subgraph Docs
    R[README]
    I[INDEX]
    A[ARCHITECTURE]
    G[GRAPH]
  end

  subgraph Code
    APP[app.js]
    SCH[schemas.js]
    CON[consensus.js]
    PLG[plugins]
  end

  subgraph Data
    J[links_105.json]
    GEN[generate_json.py]
  end

  R --- I
  I --- A
  A --- G
  APP --- J
  SCH --- APP
  CON --- APP
  PLG --- CON
  GEN --- J
```

---

## How to refresh graphs after inventory change

```bash
cd D:\trendforge_inventory_app
python -c "import json;from collections import Counter;i=json.load(open('links_105.json',encoding='utf-8'));print(Counter(x['status'] for x in i));print(len(i))"
```

Update pie counts in this file and [INDEX.md](./INDEX.md) if status totals change.

## Live snapshot flow

```mermaid
flowchart LR
  T[TrendForge AsyncEndpointClient] --> N[10 P0 normalizers]
  N --> G{Date + age + session gates}
  G -->|eligible| S[trendforge.livePanels.v1]
  G -->|invalid or stale| W[WAIT / STALE / MARKET CLOSED]
  S --> C[Clone catalog inventory]
  C --> O[Overlay by source_key]
  O --> P1[Sector]
  O --> P2[Consensus and Nifty]
  O --> P3[Screener v1.3]
  W --> B[Block score and vote overlay]
```

---

## Implemented MD69-M1 registry graph

**Status:** the exact registry, pinned hash, typed profiles, compiler, and offline
tests are implemented. No live fetch or scheduler is activated.

```mermaid
flowchart LR
  CSV["Exact 69-source CSV"] --> HASH["Pinned SHA-256 file"]
  CSV --> COMP["Typed registry compiler"]
  YAML["source_refresh_profiles.yaml"] --> COMP
  HASH --> COMP
  COMP --> GATE{"All 69 contracts valid?"}
  GATE -->|No| FAIL["Fail with source key and reason"]
  GATE -->|Yes| MATRIX["69/69 executable adapter matrix"]
  MATRIX --> ENDPOINT["Existing AsyncEndpointClient endpoint"]
  MATRIX --> RESOLVER["Existing resolver or source monitor"]
  MATRIX --> PARSER["Existing parser or normalization adapter"]
  MATRIX --> PARAMS["Parameters and provider or fan-out"]
  MATRIX --> GROUP["Response reuse or session sharing"]
  MATRIX --> POLICY["PROVISIONAL; activation_ready=false"]
  POLICY -. "M2-M7 inactive" .-> STOP["No network, DB migration, or scheduler"]
```

```mermaid
flowchart LR
  TF["D:\\TrendForge - fetch/archive/normalize/schedule"] --> SNAP["Future validated snapshots"]
  SNAP --> SPA["D:\\trendforge_inventory_app - display/catalog only"]
  SPA -. "never fetch NSE/BSE directly" .-> BLOCK["Live download blocked"]
```

Full contract: [MARKET_DATA_69_CAMPAIGN_PLAN.md](./docs/fable/MARKET_DATA_69_CAMPAIGN_PLAN.md).

Ownership remains explicit: `D:\TrendForge` owns all fetching and processing;
this inventory app remains display/catalog only.

## Pack-2 context sources (collector-only, 2026-08-10)

```mermaid
flowchart LR
  R["TrendForge 104-key registry"] --> F["Existing resolver"]
  F --> B["TradingEconomics BDI"]
  F --> Y["Yahoo BDRY ETF proxy"]
  F --> G["Google Trends India RSS"]
  B --> N["Fail-closed normalize + date + previous/change"]
  Y --> N
  G --> N
  N --> O["Raw archive + canonical object + last-good"]
  O -. "separate catalog approval required" .-> SPA["Inventory SPA"]
```

These three keys are dynamic collector contracts, not hard-coded frontend
feeds. They remain informational and zero-score. No new catalog card,
Consensus vote, or Screener term was added.

```mermaid
flowchart LR
  P3["Pack 3 candidates"] --> R["TrendForge 108-key registry"]
  R --> A["Existing resolver and shared sessions"]
  A --> Q["CRISIL / ICRA / CARE / Google News RSS"]
  Q --> V["Schema + date + age + dedupe validation"]
  V --> S["Raw archive + normalized object + last-good"]
  S --> C["Inventory catalog 150 rows / 114 keys"]
  C -. "informational only" .-> Panels["Research panels"]
  Panels -. "zero vote / zero score" .-> Guard["Consensus and Screener unchanged"]
```

## Dead-route quarantine (2026-08-11)

```mermaid
flowchart LR
  D["Verified dead/unusable route"] --> Q["TrendForge NOT_IN_USE hint"]
  Q -. "never fetch / schedule / parse / score" .-> B["Blocked from production"]
  W["Working replacement source_key"] --> R["119-key typed registry"]
  R --> S["Archive + normalize + last-good"]
  S --> C["161-row catalog / 125 active keys"]
  C -. "existing role rules only" .-> P["Research panels"]
```

Quarantined: Yahoo `^BADI`, `pytrends`, StockEdge "API", BSE `FIIDII/w`,
and BSE `ParticipantWiseOI/w`. They remain documented, but do not enter the
runtime graph. Working replacements remain active. MCX is intermittent, not
dead, so its last-good path remains enabled. Machine-readable authority:
`D:\TrendForge\config\source_route_quarantine.yaml`.

## FII-related stock-name display (2026-08-11)

```mermaid
flowchart LR
  MD["MD69 Refresh pin 123"] --> TP["Screener / Tickertape / Dhan / Equitymaster"]
  TP --> STORE["Saved last-good objects"]
  STORE --> CAT["Catalog cards 162-165"]
  STORE --> API["GET /api/institutional/fii-stock-signals"]
  DEALS["Official bulk/block + SHP"] --> API
  API --> ID["Identity: ticker / ISIN / exact name / NAME ONLY"]
  ID --> UI["Inventory strip below Nifty Filter"]
  UI -. "informational only" .-> ISO["No consensus vote / no screener score"]
  API -. "not wired yet" .-> APP["TrendForge command room frontend"]
```

Last-good 2026-08-13: Screener 105, Tickertape 300, Dhan 32, Equitymaster 25.
Dhan hold % may be null. Command-room UI is `TF-APP-FII-M1` (open).
Log: ADD_40 intake 2026-08-12.

## FII Refresh consumer edge (2026-08-11)

```mermaid
flowchart LR
  R["Refresh button"] --> C["MD69 registry collector"]
  C --> S["Canonical hashed latest objects"]
  S --> P["Sector / Consensus + Nifty / Screener"]
  S --> F["FII stock-name API"]
  F --> U["FII informational strip"]
  C --> H["Completion hook"]
  H --> P
  H --> U
```

Observed 2026-08-13: all four routes persisted and rendered. Card rows are
Screener.in 105, Tickertape 300, Dhan 32 and Equitymaster 25. The inventory FII
API emits all four groups (462 holding/reference rows total), with unresolved
identities labelled `NAME ONLY` and zero scoring/voting authority. The main
TrendForge command room does not consume this API yet.


## Embedded Source Operations flow - 2026-08-15

```mermaid
flowchart LR
  C["Compiler report"] --> P["Source Operations panel"]
  M["Runtime monitor catalog"] --> P
  A["Fetch attempts"] --> P
  O["Parser outputs"] --> P
  F["Freshness status"] --> P
  P --> S["HEALTHY / VALID_EMPTY / STALE_PARTIAL / BLOCKED / FAILED / NOT_ATTEMPTED"]
  P --> D["Research visibility and failure reason"]
  P -. "never authorizes" .-> G["TrendForge gates and public state"]
```

The panel is embedded below the KPI cards when the terminal passes `embed=terminal`.
It is observability and provenance only; it does not create a second collector,
scorer, or decision engine and cannot activate sources, emit `CONFIRMED`,
calculate quantity, or execute orders.


## Hash-pin caveat - 2026-08-15

The source and bundled runtime files are directly byte-identical for this
change, but the existing snapshot manifest still contains the pre-Source-
Operations byte sizes and hashes. The existing `inventory-workbench.test.js`
also still expects the old drawer URL without `embed=terminal`. Its current
observed result is **FAIL: Size mismatch: index.html**. This means the runtime
panel observation is valid, but the manifest/test pin must be refreshed before
claiming a clean snapshot-integrity verdict. No source data, catalog sample, or
TrendForge state authority is affected by this metadata/test discrepancy.
