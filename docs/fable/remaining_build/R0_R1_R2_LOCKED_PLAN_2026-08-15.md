# 2026-08-16 R1/R2 Readiness Audit And Corrected Build Contract

> **Current count note (2026-09-03):** The collector grew from the 123-job
> baseline used throughout this dated plan to 126 pinned jobs after adding
> `nse_esm`, `nse_price_bands` and `nse_auction_securities`. Historical
> 2026-08-16 results below remain 123-job observations. For current runs,
> interpret generic “all registry jobs” acceptance rules as 126; do not rewrite
> historical counts or treat the three restriction sources as directional
> votes.

> This section supersedes stale R1/R2 readiness statements later in this file. It does not mark R1 or R2 implemented. It is the required pre-build contract for wiring A1-C1 to the redesigned TrendForge UI.

## Verdict and observed baseline

- R1 is ready to build only under this corrected contract.
- R2 starts only after corrected R1 passes.
- No R1/R2 code was implemented in this audit.
- Latest cash run: cash-2026-08-16-manual-20260816-160551-9e7a3429071a.
- A1, A2, A3, A4, A6 and C1 completed. A5 and B were explicitly skipped. C0 was reused.
- C1 persisted 2,463 rows with WATCH_WAIT_REJECT ceiling.
- sourceActivationReady=false, canUnlockConfirmed=false and executable=false.
- GET /api/v1/selection/live is still the older R1-LIVE projection, has no schema version and returned zero candidates.
- All Stocks and Research Radar remain fixture-owned by frontend/product-fixture.js.
- frontend/app.js separately owns legacy runtime rendering, so direct wiring would create conflicting UI authority.
- Inventory Workbench remains read-only source-operations glass.
- Focused R1/A1-C1/family/source-operation tests passed 46/46.

A completed A1-C1 run is upstream evidence. It is not proof that R1/R2 is built, persisted, exposed or rendered.

### Authority check (2026-08-16) — this contract vs File A / Final Merge / Hybrid

| Authority | Verdict on **this top contract** |
|---|---|
| **File A** (`new_merge` §15 R1 DTO, R2 S0–S3, four states, no qty) | **Hold.** Remaining R1 = live evidence DTO. Remaining R2 = attention order over already-built cash S0–S3 (A1–C1). Not a second spine. |
| **Final Merge** (FMR-001/002 partial; workbench ≠ evidence/rank; R15 ≠ workbench) | **Hold.** Workbench stays glass. New APIs are TrendForge selection reads. R15 Scanner Lab is later. |
| **Hybrid (File B)** | **Hold as detail, not sequence.** Family/root caps, evidence ≠ win%, inventory is not extra votes. Do not execute Hybrid H1–H10 as the sprint. |
| **New collector/UI design** (123 jobs, 6 aliases, HTTP 200 ≠ usable, GET does not collect) | **Hold.** |

**Not File A complete:** this file is not a substitute for File A or Final Merge. It is the R1/R2 **execution contract** under them.

**Must not collide:** File A **R2-B = named source activation (closed)**. Isolated screener proof in this file is **R2-SHADOW**, never `R2-B`. **PRIMARY** is prohibited in this slice.

## Corrected responsibility split

R1 assembles evidence:

1. SourceEvidenceRecordV1: one row per canonical registry job, currently 123. Aliases reference the parent and never add jobs or votes.
2. StockEvidenceRecordV1: one row per resolved instrument, including excluded, WAIT and REJECT rows.
3. InventorySourceBundleV1: one immutable bundle with both row types plus run, universe, permission, clock and lineage identity.

R1 cannot rank or produce CONFIRMED, entry, target, stop, quantity, win probability or broker action.

R2 orders research attention. It consumes only an accepted R1 bundle and matching persisted A1-C1 outputs. It emits deterministic ordinal attention and only WATCH, WAIT or REJECT. The frozen Inventory screener is SHADOW-only and cannot vote or alter baseline authority.

## Exact file and function map

Reuse:

- backend/trendforge_api/selection/contracts.py: existing identity, PIT lineage, fact, claim and candidate contracts.
- backend/trendforge_api/market_data_store.py: attempts, last-good pointers, object hashes and manifests.
- backend/trendforge_api/market_data_registry.py: jobs, aliases, parsers and cadence.
- backend/trendforge_api/selection/store.py: versioned run/candidate JSON. No first-slice database migration.
- backend/trendforge_api/selection/cash_c1_rank.py: only after coherence, C0 and dataset-root defects below are corrected.
- backend/trendforge_api/main.py: read-only APIs. GET never downloads or recomputes.

Add:

- backend/trendforge_api/selection/inventory_source_bundle.py
  - build_inventory_source_bundle(...)
  - emits trendforge.inventory-source-bundle.v1 and persists its immutable hash.
- backend/trendforge_api/selection/attention_order.py
  - build_attention_order(...)
  - emits trendforge.inventory-discovery.v1 and owns stable order/reasons/root caps.
- backend/trendforge_api/selection/shadow_screener.py
  - run_shadow_screener(...)
  - isolated hash-pinned frontend/inventory-workbench/screener.js runner;
  - sanitized JSON input, JSON-only output, timeout/memory/row/network/write/process restrictions.

Do not add another downloader, registry, database or duplicate contract.

## R1 DTO contract

trendforge.inventory-source-bundle.v1 top-level:

- schemaVersion, bundleId, bundleHash, builtAt, asOf, tradingDate;
- collectorRunId, cashPipelineRunId, snapshotBundleId, permissionFingerprint;
- universeId/version/count, resolvedCount, excludedCount, unresolvedCount;
- sourceActivationReady, gateAuthorizedSourceKeyCount, researchCeiling, canUnlockConfirmed, executable;
- sourceRecords, stockRecords, warnings, errors.

Source row:

- sourceKey, canonicalSourceKey, aliasOf, normalizedSourceKey;
- attemptState, usabilityState, parserState, sourceSchemaVersion, parserVersion;
- httpStatus, rowCount, dataDate, publishedAt, availableAt, fetchedAt;
- cadenceState, freshnessState, authorityClass, datasetRoot, correlationGroup;
- rawObjectHash, normalizedObjectHash, lastGoodObjectHash;
- evidenceEligible, voteEligible, canUnlockReady, reasonCodes, error.

Usability states include USABLE_CURRENT, VALID_EMPTY_CURRENT, STALE_LAST_GOOD, CATALOG_ONLY, BLOCKED, FETCH_FAILED, PARSE_FAILED, SCHEMA_MISMATCH, MISSING_REQUIRED_PARAMETER and NOT_APPLICABLE. HTTP 200 without populated parsed trading records is not usable. Valid-empty remains distinct from failure.

Stock row:

- identity, state/ceiling/direction;
- attempted/completed/empty/failed/not-attempted sources;
- family/root coverage, support/opposition/missing/conflicts;
- sourceClock, lineage, restrictionState, tradabilityState;
- whyVisible, whyNotConfirmed, warnings;
- null entry/target/stop/riskReward with STRUCTURE_NOT_AVAILABLE_UNTIL_R5.

## R2 DTO contract

trendforge.inventory-discovery.v1 contains schema/run/bundle/formula identity, profile, mode, date, activation, ceiling, universe/state counts, rows, shadowComparison, warnings and errors.

Each row contains symbol, state, ceiling, direction, displayOrder, nullable attentionRank, attentionPriority/band, support/opposition/missing/conflicts, completeness, freshness, sourceQuality, restrictions, reasons and lineage. Trade geometry stays null.

attentionPriority is ordinal research priority, not evidence strength or win probability.

## Coherent snapshot and permission gates

R1/R2 fail closed unless inputs share one collectorRunId, cashPipelineRunId, tradingDate, immutable snapshotBundleId and persisted C0 permissionFingerprint.

R2 must not use a newly built or unmatched C0 matrix. Failures:

- WAIT_PERMISSION_MATRIX_MISSING;
- WAIT_PERMISSION_MATRIX_MISMATCH;
- WAIT_MIXED_SNAPSHOT_INPUTS;
- WAIT_LINEAGE_INCOMPLETE.

Skipped A5/B is missing evidence, never numeric zero.

## Dataset-root and ordering rules

Return, volume and turnover from one nse_bhavcopy_eod object are multiple features from one root, not independent confirmation.

R2 carries datasetRoot/correlationGroup, caps at root before family aggregation, versions cash formula as ATTN-CASH-V1, avoids hidden renormalization, handles missingness/completeness/freshness/quality explicitly, and sorts by state bucket, attention priority, symbol and stable identity. REJECT remains visible with null rank and stable displayOrder.

## Shadow rules

Only BASELINE and SHADOW are allowed in R2. PRIMARY is prohibited.

SHADOW verifies frozen hash, accepts at most 500 sanitized rows, has no network/write/secrets/child-process/DOM access, enforces timeout/memory, emits trendforge.inventory-shadow.v1 and leaves BASELINE unchanged on every failure. Three identical inputs must produce byte-equivalent normalized outputs.

## Trigger, persistence and APIs

collector commit
-> A1-C1 once per collector run
-> accepted C1 builds/persists R1 once
-> accepted R1 builds/persists R2 BASELINE once
-> optional SHADOW after baseline
-> read-only APIs serve completed immutable payloads
-> frontend reads; GET never starts work

Idempotency: (collectorRunId, cashPipelineRunId, bundleHash, formulaVersion, mode). Failed/partial builds never replace latest completed.

Add:

- GET /api/v1/selection/evidence
- GET /api/v1/selection/attention
- GET /api/v1/selection/attention/{symbol}

Keep /api/v1/selection/live as legacy synthetic WAIT projection with legacyProjection=true. Do not repurpose /api/radar. Keep /api/source-operations/snapshot operations-only.

No completed R1/R2 returns structured 503 WAIT_R1_BUNDLE_UNAVAILABLE or WAIT_R2_DISCOVERY_UNAVAILABLE. Completed empty universe returns HTTP 200 VALID_EMPTY_UNIVERSE. Stale output keeps original lineage and non-confirming ceiling.

## Frontend integration

product-fixture.js and app.js must not both own live All Stocks/Radar DOM.

1. Pass R1 backend/API before UI.
2. Pass R2 baseline/shadow before UI.
3. Add one schema adapter and one exclusive live renderer.
4. Keep fixture preview labeled until live adapter succeeds.
5. Never merge fixture entry/target/stop into live rows.
6. On failure show stale last-completed live data or WAIT; never silently substitute fixtures.

Live R1/R2 rows may show identity, WATCH/WAIT/REJECT, attention reason, freshness/completeness/quality, support/opposition/missing/restrictions/lineage and why-visible/ranked/not-confirmed. No live entry, target, stop or risk/reward before R5.

Inventory Workbench stays read-only and cannot write selection state, score, activation, quantity or execution.

## Acceptance tests

R1:
1. One source row per canonical job; aliases do not add votes.
2. One stock row per resolved instrument including WAIT/REJECT/excluded.
3. HTTP 200 empty/malformed is not usable.
4. Valid empty differs from fetch/parse/schema failure.
5. Stale last-good cannot confirm.
6. Exchange cadence handles non-trading days.
7. Unknown date produces freshness WAIT.
8. Catalog/fixture samples never enter evidence.
9. Mixed runs/dates fail closed.
10. Missing/mismatched C0 fails closed.
11. Skipped A5/B is missing, not zero.
12. Identical input gives identical bundle hash.
13. Failed build preserves latest completed.
14. No-confirm/no-execution ceilings remain.
15. Trade geometry is null.

R2:
16. Unaccepted R1 is rejected.
17. Same-root features are capped.
18. Missing inputs do not secretly renormalize.
19. Ties use stable identity order.
20. All rows remain visible; REJECT rank is null.
21. Identical input gives identical BASELINE.
22. Shadow failure leaves BASELINE unchanged.
23. Three shadow runs are deterministic.
24. VM cannot access forbidden capabilities.
25. SHADOW cannot alter state/ceiling/score/authorization.
26. PRIMARY is rejected.
27. Non-cash families are NOT_APPLICABLE_TO_CASH_R2.
28. Only WATCH/WAIT/REJECT output.

API/UI:
29. APIs expose schema/run/lineage.
30. GET triggers no work.
31. Legacy live route remains compatible/labeled.
32. One live renderer; fixture/live never mix unlabeled.
33. Unavailable/empty/stale/partial/overflow differ.
34. Live cards contain no trade geometry.
35. Source Operations remains read-only.
36. Keyboard/text-fit/desktop/mobile checks pass.

Run focused R1 before R2, focused R2 before UI, then complete backend/frontend plus refresh, A1-C1, BSE recovery and Workbench integrity. Completion requires observed API and rendered behavior.

## Milestone order

1. R1-A contracts and coherent immutable bundle.
2. R1-B persistence, read-only API and fail-closed tests.
3. R1-C observed API behavior and status/validation.
4. Stop for R2 approval.
5. R2-ATTN baseline attention and root rules.
6. R2-SHADOW isolated shadow and three-run proof. **Not** File A R2-B activation.
7. R2-API + minimal exclusive live UI adapter on TrendForge command room (not workbench). This is not R15 complete.
8. Stop. File A **R3 locked contract is §13** (not started). File A R2-B activation stays closed. Do not re-audit R3 before build — execute §13 only.

## Stale statements superseded

Later claims that the cash track is unobserved, CAD-004 is unimplemented, BSE financial/shareholding remains broken or Workbench integrity is unverified are stale. Current evidence shows the observed full-registry refresh, automatic A1-C1, repaired BSE session recovery and verified Workbench files. This foundation does not make R1/R2 complete.

---
# R0 / R1 / R2 locked execution plan

**Date:** 2026-08-15  
**Revised:** 2026-08-16 (R1/R2 remaining split from done A1–C1; UI not connected)  
**Status:** Execution plan only — not a third build spine. Cash A1–C1 **done**. R1 DTO + R2 attention **live**. File A R3 is **specified in §13, not started**.  
**Authority:** File A `new_merge_PLAN_2026-07-18.md` §9 S0–S3, §11 FUS-009, §15, §25.20.1, **§25.25.4–25.25.13**  
**Evidence:** `docs/BUILD_STATUS.md`, `docs/VALIDATION.md`, `selection/contracts.py`, `feature_registry.py`  
**Does not:** activate sources, emit live CONFIRMED, compute quantity, chase 117/129 voting, or treat `canVote=false` as rank permission

---

## 0. Locked product law

```text
A1  SourceResult + parsed staging rows (no instrument_id required)
A2  Identity → NormalizedFact + S0/S1 safety
    …
    → dataset-root + event identity (keep every fact)
    → freshness and authority quality
    → correlation-family resolution
    → strongest support AND strongest opposition per group
    → hard gates and missing requirements
    → priority WATCH / WAIT / REJECT
```

**Rank rule:** quality-weighted, same-direction, independent families **after** gates, and only if the **compiler/governance contract** says `can_rank=true`.  
Family count is a chip. More hits is not a better stock.

**Permissions live on the versioned source contract (compiler), not on the resolver profile.**

| Flag | Owner | Meaning now |
|---|---|---|
| `can_rank` | Compiler / source contract | May enter S3 attention rank. Default **false** until C0 + C |
| `can_veto` | Compiler / source contract | May REJECT/WAIT only when artifact, date, schema, freshness **and** this flag pass |
| `can_unlock_confirmed` | Compiler / source contract | Always **false** in this plan |
| R0-B `canVote` | Cohort proof only | **Not** rank or veto permission |

The resolver **only consumes** those flags. A profile must never authorize its own sources.

**Veto proof:** `gateAuthorized=0` today. Ban may veto only with a fresh, schema-valid, dated artifact **and** `can_veto=true`. Failed or stale restriction data → **WAIT**, never a fake pass or fake REJECT.

**Direction (A3):**

- Previous close → **return direction** (up/down/flat).  
- PIT percentile → **relative importance**, not direction.  
- Support / opposition exists only after a **deterministic profile** evaluates both.

**Stock card:**

```text
Independent support: (after profile evaluation)
Opposition: (after profile evaluation)
Gate pass: not banned              ← eligibility, not a plus family
            (or WAIT_RESTRICTION if ban artifact stale/failed)
Missing: closed structure, and any required-for-profile item
Event identities: aliases/mirrors of ONE economic event collapsed
                  different trades/counterparties/dates kept separate
Last-good age: observed_at + age (stale visible, not ranked)
State: WAIT
Priority: high attention, not confirmed
```

**Labels:** event/sponsor enrichment; participant OI = regime context; indices = context; Nifty 500 = universe; market status = session gate; delivery = delayed swing; AMFI/CFTC = delayed context; CA = adjustment/integrity.

**Hard rules (keep all prior + these):**

1. Gates are not plus families.  
2. Conflict → WAIT.  
3. Quality beats family count.  
4. Deals enrich; collapse **only same-event aliases/mirrors**.  
5. Fallback cannot replace official valid-empty.  
6. Generated purpose map; no hand 129-row file.  
7. Consensus v4 is not File A resolver.  
8. No standalone three-source rewrite.  
9. `canVote=false` is not `can_rank`.  
10. One bhav row is not support.  
11. F&O OI is contract-safe (underlying + instrument + expiry; no option/futures mix).  
12. Every **claim** uses a registered FTR. A3 cash screens are **§25.25.4 `DISC_EOD_*`** (or `discovery_reason` until those FTRs exist). **Do not use `FTR-018` for cash bhavcopy** (`FTR-018` is intraday activity).  
13. Keep every fact. Dedup key = dataset root + symbol + session + contract/expiry + **event identity**.  
14. CA is integrity; unresolved → WAIT. Replay must not see a future CA (`available_at`).  
15. MWPL stays `MWPL_MISSING` until official % proof. **B does not block cash ranking.** Profiles that require MWPL stay WAIT.  
16. Segment-aware profiles. Missing F&O does not punish cash-only names.  
17. Last-good ≠ fresh.  
18. **A1 must not create `NormalizedFact`.** That type requires `instrument_id` (`contracts.py`). Staging first.

---

## 1. Already built

Unchanged: R0-A closed; R0-B reviewed `canVote=false`; R0-C quarantined; R1 STO WAIT rows; resolver fixture exists; DAT-010/011 registry; activation false; MWPL % artifact missing; index close not in 123 registry.

**Cash research path A1–C1 is implemented** (modules + tests). Post-commit can dispatch after a cash-relevant last-good. Collector Refresh is 123 registry jobs (165 cards / 129 keys / 6 aliases). Source Operations snapshot exists as **observability only**.

**Do not rebuild A1–C1 as “R1/R2.”** Those letters are the cash spine. File A **R1** and **R2** below are the remaining live-evidence DTO and attention-order work.

---

## 2. Missing pieces (updated)

| Gap | Correction |
|---|---|
| A1 facts too early | Persist `SourceResult` + parsed rows only |
| `FTR-018` on bhavcopy | Forbidden. Add §25.25.4 cash-discovery FTRs, or emit `discovery_reason` only |
| Flags on resolver profile | Move to compiler/source contract |
| Ban veto without proof | Stale/failed ban → WAIT, not REJECT |
| Direction = prior close alone | Profile must combine return + PIT importance |
| Collapse all deal cards | Collapse aliases of **one event** only |
| A4 history without CA vintages | Store factor, effective date, `available_at`, revision, series version |
| A5 “join index” | A5 **owns** index collector: parser, profile, registry, pin/digest, freshness, tests |
| Use matrix unowned | **C0** before any ranking |
| B blocks the train | B is conditional; cash A3/C may proceed |

---

## 3. Feature / profile mapping

| Work | Contract | Notes |
|---|---|---|
| Cash S3 screens | File A §25.25.4 `DISC_EOD_MOMENTUM`, `RECOVERY`, `RANGE`, `LIQUIDITY`, `NARROW_SESSION` | Register as FTRs before claims, **or** store `discovery_reason` only until then |
| Intraday activity (later) | `FTR-018` | Not cash EOD |
| Safety / ban / ASM / GSM / T2T | `FTR-035` | Veto only with proven artifact |
| Delivery (later) | `FTR-019` | Delayed swing |
| Market / sector context | `FTR-002` / `FTR-003` | A5 after index source is registered |
| Structure (later R5) | `FTR-006` / `FTR-007` | Not A3 |

---

## 4. Implementation flow (corrected)

Each letter **passes focused + regression tests** before the next. B is the only **optional** branch.

```text
A1  Cash SourceResult + parsed staging rows
A2  Identity → NormalizedFact + S0/S1 safety
A3  Registered cash-EOD discovery profiles → WATCH
A4  PIT history, baselines and adjusted-series vintages
A5  Verified index collector + context + CA integrity
A6  Contract-safe F&O shortlist enrichment
C0  Generated source permission/use matrix
C1  Resolver rank only for can_rank=true sources
B   Conditional MWPL when an official percentage artifact exists
```

§25.25.13 map: A1=1 (data only), A2=2, A3=3, A4=4, A5=5, A6=6, C0+C=7.

### A1 pass

- Last-good cash file → `SourceResult` + parsed staging rows + hash + session date + age.  
- No `NormalizedFact`, no public state, no direction.  
- Valid-empty / stale / blocked / parse-fail distinct.

### A2 pass

- `instrument_id` resolved; `NormalizedFact` created.  
- S0/S1 identity + calendar + tradability.  
- Restriction fail/stale → WAIT, not invented REJECT/pass.

### A3 pass

- Eligible cash universe WATCH/WAIT/REJECT from **registered cash-EOD profiles** or `discovery_reason` only.  
- `FTR-018` unused.  
- Same artifacts replay to the same states.

### C0 pass (before C)

- Compiler report lists every in-scope source: desk, job, family, `can_rank`, `can_veto`, ceiling.  
- Resolver reads those fields; profiles cannot override them.

---

## 5. Adversarial tests (required)

Prior list, plus:

| Case | Expected |
|---|---|
| A1 writes `NormalizedFact` | Must fail / forbidden |
| Claim uses `FTR-018` on bhavcopy | Rejected |
| Profile sets `can_rank` itself | Fail closed |
| Stale ban file | WAIT, not REJECT and not “gate pass” |
| Two deal cards, same event alias | One event identity |
| Two deal cards, different times/parties | Two event identities |
| Future CA `available_at` | Invisible to earlier replay |
| Cash rank with `MWPL_MISSING` | Allowed unless profile requires MWPL |
| C without C0 | Forbidden |

---

## 6. Not in this plan

117/129 gates, GPT S0–S5, family-count rank, Consensus v4 as resolver, FTR-018-for-bhav, NormalizedFact in A1, MWPL as a hard sequence gate, live CONFIRMED, qty, broker.

---

## 7. Coding tickets

**A1 done:** cash last-good → `SourceResult` + staging rows.

**A2 done:** identity → `NormalizedFact` + S0/S1. Ban veto only when proven.

**A3 done:** §25.25.4 WATCH reasons (`DISC_EOD_V1`). `FTR-018` unused. `can_rank` still false.

**A4 done:** immutable RAW cash sessions, PIT CA vintages, CROSS-020 adjusted series, baselines.

**A5 done:** index context contract + CA integrity overlay.  
**A6 done:** contract-safe futures enrichment on WATCH shortlist.  
**C0 done:** generated permission matrix.  
**B done:** conditional MWPL (`MWPL_MISSING` unless proven).  
**C1 done:** attention rank only when C0 `can_rank=true`.

Named source activation and live CONFIRMED remain closed.

---

## 8. One-line sequence

**Stage cash rows → identify → cash WATCH profiles → history vintages → real index source + CA integrity → F&O shortlist → C0 matrix → optional MWPL → C1 rank only with compiler `can_rank`.**

---

## 9. Remaining File A R1 (live stock evidence) — 2026-08-16

R1 is **not** another A1–C1. R1 is the live evidence object a human or later UI can trust.

| Ticket | Build | Do not |
|---|---|---|
| `R1-DTO` | One live row per **registry contract** (123 jobs), not 165 cards | Iterate catalog cards or companions as evidence |
| `R1-ALIAS` | Resolve the 6 catalog family names onto the parent job (`nse_block_deal_live` ← `nse_block_deal`, and the other 5) | Exact-key miss treated as “no last-good” |
| `R1-ELIG` | `EVIDENCE` / `VALID_EMPTY` / `CATALOG_ONLY`. Envelope-only / junk HTML / HTTP 200 / stale last-good ≠ EVIDENCE | Raise research-usable to 129 |
| `R1-CLOCK` | Cadence-aware clocks (publication window, session, weekly/event). Friday bhav on Sunday can be current | `data_date != today` as universal stale |
| `R1-WHY` | `missing_evidence` + `why_not_confirmed` + `evidence_strength` labelled **“Evidence strength - not win probability”** | Combined_Score / win% |
| `R1-BUNDLE` | `trendforge.inventory-source-bundle.v1` from last-good + parsers + PIT lineage (`evidenceAsOf`, SHA-256) | Catalog `records_sample` / `sample_row` |
| `R1-RADAR` | Live radar/discovery response from this DTO (not only Q5 fixtures) | Pretend `/api/radar` is already R1 |

**Inputs:** `market_data_latest` + alias map + compiler flags + source-operations facts.  
**Outputs:** bundle + why-not-confirmed. **No rank. No public state change. No CONFIRMED.**

`nse_index_close_eod` and MWPL % are still **not** in the 123 registry. R1 must say they are missing, not invent them.

---

## 10. Remaining File A R2 (attention ranking) — 2026-08-16

R2 is **not** “build S0–S3 again.” Cash S0–S3 already lives in A2/A3/C1.

| Ticket | Build | Do not |
|---|---|---|
| `R2-ORDER` | Attention order over existing A1–C1 cash states | Rebuild staging/identity/discovery |
| `R2-SHADOW` | Frozen `screener.js` v1.3 via Node VM; `trendforge.inventory-discovery.v1`; `authority=DISCOVERY_QUEUE_ONLY`; ≤500; ≥3 deterministic shadow runs | Port formulas to Python; edit scoring engines |
| `R2-FAMILY` | Only cash/index dependencies enter cash A1–C1. Derivatives, deals, events, commodity, macro get their own disposition or skip | Every Refresh job ranked as cash |
| `R2-MODE` | **BASELINE** and **SHADOW** only in this slice. **PRIMARY prohibited** (same as top contract) | Flip PRIMARY; treat shadow as production rank |
| `R2-B` | File A **named source activation**. Live ledger is WAIT-only (`r2b_live.py`, `GET /api/v1/selection/named-activation`). Names R0-B sources; `sourceActivationReady` stays false; none may confirm. | Call the ledger an unlock; set `sourceActivationReady=true`; emit CONFIRMED |

**Public state stays `WATCH | WAIT | REJECT`.** Quality-weighted, same-direction, independent families after gates, and only if compiler `can_rank=true`. Inventory A-score is a **chip**, not a vote.

**Not in R1/R2:** CAD-004 scheduler-in-lifespan, adding `nse_index_close_eod` / MWPL % to the registry, R12 options, live CONFIRMED, qty, 117/129 voter gates.

**Average effort (focused):** R1 ~1–2 days; R2 ~3–5 days. Grows if R2 is treated as a new S0–S3 or a 165-link ranker.

---

## 11. New UI integration page is NOT connected to R1/R2 — locked

The Inventory Workbench drawer (`/inventory-workbench/?embed=terminal`) and Source Operations panel are **glass + collector observability**. They are **not** the R1 evidence page and **not** the R2 ranking page.

| Surface | What it shows now | What it does **not** show |
|---|---|---|
| Catalog cards / KPI bar | 165 static/filled samples, collapsed primaries | Live R1 eligibility or why-not-confirmed |
| Refresh button | Starts 123-job MD69 collect | Stock rank, WATCH list, C1 order |
| Source Operations | Compiler / last-good / HEALTHY vs STALE / cash A1–C1 **stage lamps** if a post-commit snapshot exists | Per-symbol live evidence, missing_evidence, attention rank |
| Consensus / Screener in the workbench | Frozen inventory engines on catalog or live-panel overlay | File A resolver / C1 `can_rank` rank |
| Host TrendForge command room | Drawer chrome + other shells | Wired R1 DTO or R2 queue |

**Law:** R1/R2 live stock evidence and ranking **must be built in TrendForge first** (`inventory-source-bundle.v1`, live radar/DTO, C1 attention). Connecting that object to the workbench or a new stock card is a **later, separately approved frontend ticket**. Do not treat Source Operations “5 usable / 97 last-good” as a stock rank. Do not paint catalog samples as live R1 evidence.

Until that ticket exists, the honest UI sentence is:

```text
Collector health is visible.
Live stock evidence (R1) is not on this page.
Attention ranking (R2) is not on this page.
```


## Source Operations UI note - 2026-08-16

The embedded Inventory Workbench Source Operations panel is a verification
surface for **collector and cash-track status only**. It does not implement
R1 DTO or R2 rank, does not change File A order, and cannot activate sources,
emit CONFIRMED, or compute quantity. Valid-empty remains distinct from failed.


## Hash-pin / overlay - 2026-08-16

Declared overlay re-pin is done (`inventory-workbench.manifest.json`;
`inventory-workbench.test.js` 24 files verified). Scoring engines stay frozen.
This is snapshot integrity, not R1/R2 UI integration.

## Execution bridge status - 2026-08-15

The existing A1-C1 implementation is now reachable from the collector post-commit event. This is wiring and observability work, not a new milestone spine and not a rebuild of A1-C1.

verified parsed save -> last-good/hash/date -> relevant fingerprint -> A1 -> A2 -> A3 -> A4 -> A5 -> A6 -> C0 -> conditional B -> C1

Refresh and Scheduler share the bridge. Unrelated source changes skip it; the same fingerprint runs once; failed downstream work becomes FAILED_STAGE; the collector last-good is retained. C0 permissions are reused unless compiler or contract inputs change. No current MWPL percentage artifact means B remains MWPL_MISSING.

Observed cash run `cash-2026-08-16-manual-20260816-160551-9e7a3429071a` completed A1–A4, A6, C1 (2463 rows, WATCH_WAIT_REJECT); A5 and B skipped as missing, not zero. That proof is **not** R1 DTO and **not** workbench ranking. `C1 can_rank=true` is cash attention permission after C0, **not** File A R2-B activation (`sourceActivationReady` remains false). Overlay re-pin (CAD-005) is done. Next File A build tickets are the **top contract** R1 then R2-ATTN/R2-SHADOW. The workbench stays disconnected.

## Download coverage - 2026-08-15

Inventory Refresh is the TrendForge MD69 collector. The SPA never fetches NSE/BSE.

| Layer | Count | Meaning |
|---|---:|---|
| Catalog cards | 165 | Display rows, including companion/provenance duplicates |
| Unique inventory keys | 129 | Card `active_source_keys` |
| Collector registry jobs | 123 | What Refresh actually fetches |
| Catalog-only aliases | 6 | Same parent job (`nse_block_deal_live` ← `nse_block_deal`, etc.) |

Refresh does **not** iterate 165 cards. Companion cards are not extra votes or extra downloads. HTTP 200 / junk HTML / empty / stale is not usable.

**Blocker found and fixed:** API was started without `MARKET_DATA_69_ENABLED=1` + `MARKET_DATA_69_PROVISIONAL_OVERRIDE=1`, so `POST /api/market-data/refresh` returned 503. `run_server.py` now defaults those flags on for local API start. Snapshot last-good also resolves normalized aliases so a catalog family name is not reported as missing when its parent job is already stored.


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
- `mcx_bhavcopy`, `bse_financial_results_xbrl` and `bse_shareholding_pattern` are explicit stale last-good fallbacks and require repair.

The validated pending workbook `data/reports/SOURCE_LINK_INVENTORY_MASTER.updated.xlsx` contains `CADENCE_SUMMARY` and `CADENCE_AUDIT` sheets with URL, cadence, observed/derived data date, actual parsed-row count, usability class, dispatch rule and required next action for every registry source. Replacing the canonical workbook is awaiting separate explicit approval.

### Binding design decisions

1. **Freshness is publication-aware.** A source is evaluated against its reviewed timezone, calendar, cadence, publication window, allowed lag, valid-empty rule and profile need. `data_date != today` is never a universal stale rule.
2. **Usability is content-aware.** HTTP 200, collector success, parser invocation and one-row status/schema envelopes do not prove usable data. Successful empty remains distinct from failure and from populated records.
3. **A1-C1 remains cash-family only.** Manual Refresh may fetch all registry jobs, but the post-commit router sends only current cash/index dependencies into A1-C1. Derivatives, ownership/deals, corporate events, commodity/global and macro/fund-flow sources require their own family processors or an explicit no-downstream-work disposition.
4. **Manual and automatic collection share one dispatcher.** Both paths commit raw/normalized/manifest/last-good evidence first, then dispatch only changed, cadence-current family inputs. Repeated fingerprints are idempotent.
5. **Scheduler lifecycle must be real.** `run_server.py` enables the collector, but the current FastAPI lifespan starts scanner restore and live panels only; it does not call `MarketDataScheduler.start_foreground()`. The automatic schedule is therefore planned, not implemented.
6. **Snapshot integrity must describe overlays honestly.** Current comparison found 18/24 source/bundled files identical and six intentional/drifted files different: `index.html`, `styles.css`, `app.js`, `INDEX.md`, `ARCHITECTURE.md`, `GRAPH.md`. Do not claim 24/24 identity until either re-synchronized or governed by a declared overlay manifest.

### Implementation milestones

| ID | Scope | Required result | Acceptance ceiling |
|---|---|---|---|
| `CAD-001` | Compile reviewed cadence contracts | Add timezone/calendar, publication rule, grace window, temporal field source, valid-empty semantics, family and evidence authority without creating a second registry | Provisional/unverified cadence cannot authorize freshness or activation |
| `CAD-002` | Cadence-aware freshness evaluator | Produce `NOT_DUE`, `CURRENT_FOR_CADENCE`, `LATE`, `DATE_UNKNOWN`, `VALID_EMPTY`, `STALE_LAST_GOOD` and typed failure states from publication contracts | Old weekly/monthly/event dates are not stale by age alone; unknown required dates fail closed |
| `CAD-003` | Post-commit family router | Dispatch changed successful artifacts by cash, derivatives/options, ownership/deals, corporate events, commodity/global and macro/fund-flow family | Cash A1-C1 runs once only when its required cash dependency set is session-current; unrelated families never enter A1-C1 |
| `CAD-004` | Server scheduler lifecycle | Start one foreground scheduler task in FastAPI lifespan, expose running/last-tick/next-due state, cancel on shutdown and prevent duplicate CLI/server schedulers with the existing lease | No automatic-run claim until startup, due-slot, dedupe and shutdown behavior are observed |
| `CAD-005` | Inventory snapshot overlay contract | Replace false identity with either full re-pin or a manifest containing upstream hash, bundled hash and allowed modified-file list | Undeclared drift fails; `live_panels.js` and `links_105.json` remain hash-checked |
| `CAD-006` | Operations UI and workbook projection | Show cadence, expected publication, observed date, actual parsed rows, usability, next due, family dispatch and failure reason | Observability only. This is **not** R1 stock evidence and **not** R2 ranking. No activation, CONFIRMED, quantity or execution |

### Required adversarial tests

1. Sunday refresh accepts Friday NSE EOD as the latest session and can run cash A1-C1 when the complete required set is current.
2. A prior-Friday value is rejected after a newer trading session should have published.
3. Weekly data within its reviewed release window is current; the same age under an intraday contract is stale.
4. Monthly/quarterly data inside its publication window is not mislabeled stale.
5. Event date and fetch freshness remain separate.
6. Missing `data_date/published_at/available_at` emits `DATE_UNKNOWN` when the contract requires it.
7. HTTP 200 with schema/status envelope yields zero actual parsed records and cannot dispatch.
8. Valid-empty is accepted only for a reviewed empty rule and never supplies candidate rows.
9. Stale last-good remains visible but cannot dispatch as current.
10. Manual Refresh still attempts exactly the 123 registry jobs, not 165 display cards.
11. The family router invokes cash A1-C1 only for its required changed dependencies.
12. Derivatives, ownership, event, commodity and macro changes never invoke cash A1-C1.
13. Same relevant fingerprint is processed once across manual and scheduled paths.
14. Scheduler starts once in the API lifecycle, reports next due, and cancels cleanly.
15. A second CLI/server scheduler cannot acquire the same lease.
16. Closed-day and holiday rules choose the correct expected session/publication.
17. Parameter/date-template errors cannot masquerade as successful current data.
18. Overlay manifest accepts only declared modified files and rejects a seventh undeclared difference.
19. Full backend/frontend regressions pass after focused tests.
20. Public state remains WATCH/WAIT/REJECT until separate source activation and confirmation gates pass.

### Build order

`CAD-001 -> CAD-002 -> CAD-003 -> CAD-004 -> CAD-005 -> CAD-006`. Implement and verify one milestone at a time. This section is the approved planning record only; runtime changes are not claimed here.

---

## 12. R3–R15 future-build debug (2026-08-16) — before any wiring

This is a **plan debug**, not a build. Q5-R3…Q5-R7 remain at **fixture ceilings**. Live product still stops at WATCH/WAIT/REJECT until R2-B activation. The new Inventory Workbench is **not** the R15 Scanner Lab and **not** an input to R3–R14.

### 12.1 Four parallel paths (the main run issue)

If a future ticket wires the wrong path, the result will look like a rank or a CONFIRMED and be false.

```text
Path A  last-good → post-commit → A1–C1 cash stages
        functions: stage_cash_last_good, build_cash_identity_batch,
                   build_cash_discovery_batch, build_cash_history_batch,
                   build_cash_context_batch, build_fo_enrichment_batch,
                   build_source_use_matrix, assess_mwpl, build_cash_rank_batch
        files: selection/cash_*.py, index_a5_context.py, fo_a6_enrichment.py,
               use_matrix_c0.py, mwpl_b.py, cash_post_commit.py
        result today: cash research stages + R1 bundle + R2 attention after post-commit.
        C1 can_rank may be true (attention). sourceActivationReady stays false.

Path B  Q5 fixture spine
        functions: resolve_evidence, analyze_closed_bar_structure,
                   build_enrichment_plan, evaluate_mcx_contract,
                   evaluate_option_chain, build_q5_r3_fixture_batch
        files: selection/resolver.py, structure.py, enrichment.py,
               mcx_contracts.py, options_domain.py, r2_fixtures.py,
               r3_fixtures.py, r4_fixtures.py, r6_fixtures.py
        result today: fixture-only four-state demos, including one EOD CONFIRMED
                      that is production_authorized=false

Path C  command-room radar
        functions: build_live_selection_run; GET /api/radar
        files: selection/live_run.py, decision_fixtures.py, frontend/app.js
        result today: WAIT projection / fixture radar. Not A1–C1. Not resolver.

Path D  Inventory Workbench / Source Operations
        functions: ManualRefreshCoordinator.start, build_source_operations_snapshot
        files: frontend/inventory-workbench/*, source_operations.py
        result today: 123-job collect + health lamps. Not stock evidence. Not rank.
```

**Expected R3–R15 result cannot come from Path D.**  
**Expected live R3 result cannot come from Path B alone.**  
**Expected R15 result cannot come from Path C fixture radar.**

Required future join (do not invent a fifth downloader):

```text
R1 DTO (from Path A last-good + aliases)
  → R2 attention order (over A1–C1 states)
  → R3 resolve_evidence on those claims (Path B function, live inputs)
  → R6/R8/R11/R12/R14 enrich only the shortlist
  → R15 Scanner Lab on TrendForge frontend (FINAL_PRODUCT IA)
```

### 12.2 Per-milestone: expected result, current code, gap, run issue

| Step | File A expected result | What exists now | Leads to expected live result? | Gap / run issue if built naively |
|---|---|---|---|---|
| **R3** | FUS-009 family cap; conflicts visible; missing family not renormalized | Fixture `resolve_evidence` only. Live R1/R2 exist. **Locked how-to: §13.** | Live **not** done | See §13. Do not invent a new plan at build time. |
| **R4** | Zero unknown IDs; PK pin; no runtime sidecar trust | Live `r4_live.py` + `GET /api/v1/selection/identity-pin`. Uses A2 IDs. PK inventory digest, zero vote. `r4_fixtures.py` remains Q5-R4 enrichment/MCX/options fixture. | **Live pin is done.** Silent unknown IDs are forbidden; missing A2 is `UNKNOWN_ID`. | Calling A2/A4/R5 “R4”. Treating `r4_fixtures.py` as live R4. Letting PK vote. Using scripCode as identity. Unlocking CONFIRMED. |
| **R5** | First honest **EOD swing CONFIRMED** only with closed-bar + independent context | Live `r5_live.py` + `GET /api/v1/selection/structure` at `LIVE_WAIT_REJECT_ONLY`. Official cash + index companion, IST session phases, setup tags. Fixture Q5-R3 still requires one CONFIRMED. Live `confirmedCount=0`. | **Live WAIT-only is done.** File A first CONFIRMED is **not** this milestone. | Treating setup tags as buys. Unlocking CONFIRMED before R2-B + R14. Using UTC as the NSE session clock. Adding `nse_index_close_eod` as a 124th voter. |
| **R6** | Bounded shortlist enrichment (surveillance, pledge, deals, delivery, FO if valid) | `build_enrichment_plan()` fixture; live **A6** is futures-only on WATCH shortlist | **Partial.** A6 ≠ full R6. | Rebuilding A6 as R6. Counting pledge/deal catalog companions as extra families. Envelope-only last-good dispatched as enrich. |
| **R7** | Isolated PK shadow; cannot alter state | `pk_compatibility.py`, `pk_fixture_worker.py` | **Yes if kept isolated.** | Importing PK into live `resolve_evidence` or workbench Consensus. |
| **R8** | Native core scanners (breakout, compression, volume, NR, trend) under family caps; S3 may use them | `scanners/` has **no** native registry — PK only | **No.** | Using workbench `screener.js` extractors as R8. 165-card scanner storm. |
| **R9** | Lifecycle / ORB / VWAP only on verified bars; no repaint | `transitions.py`, `history_validation.py` | **Not live.** | Running ORB/VWAP on catalog samples or unverified candles. Auto-session bars assume scheduler lifespan (CAD-004 still open). |
| **R10** | Pipe DSL; stage counts deterministic; pipe contributes **zero** claims | **No** `pk_pipe` module | **No.** | Treating Consensus v4 / workbench plugins as pipes. Vote inflation. |
| **R11** | Swing RS/delivery + MCX master gates; MCX WAIT without local master | `evaluate_mcx_contract()` fixture; `mcx_bhavcopy` last-good can be **stale fallback** (2026-08-16) | **No for live MCX.** | Unlocking MCX from a stale last-good or workbench MCX card. Daily FBIL ≠ live USD/INR (CROSS-009). |
| **R12** | Shortlist options timeline; fresh/unknown/stale; no independent confirm | `evaluate_option_chain()` static (`can_support_confirmed` forbidden); derived `option_greeks_calculated_v1` / `pcr_max_pain_history_v1` are `scoreEligible=false` | **Partial contract, no live timeline.** | Reading catalog `nse_option_chain` companion instead of `nse_option_chain_equity` last-good. Greeks as votes. Workbench option schemas as R12. |
| **R13** | Remaining deterministic scanners in family batches | Missing | **No.** | Same as R8. |
| **R14** | Official CA/sponsor join; discovery cannot confirm before join | Live `r14_live.py` + `GET /api/v1/selection/ca-join` at `LIVE_CA_JOIN_WAIT_ONLY`. Reuses `corporate_actions.reconcile_corporate_actions` (DAT-022); joins R2 rows via the R4 A2 instrument pin; hash-scoped to R1/R2/R4; R5 consumes the join (`r14RunId`/`r14RunHash`). Pipeline `R4 → R14 → R5`. Record: §13.14. | **Live WAIT-only join is done.** Sponsor/event votes stay R6. | R5 CONFIRMED on unadjusted bars. Future CA visible to earlier replay. Unlocking CONFIRMED. Pasting S4/S5 into R5. Rewriting DAT-022. |
| **R15** | Scanner Lab: All Stocks + radar + inspector from **canonical DTOs**; no radar-column explosion | `docs/TRENDFORGE_FINAL_PRODUCT.html` fixtures; command room mixes `/api/radar`; workbench is glass | **No.** Wrong page if workbench is used. | Binding R15 to `/inventory-workbench`. Replacing fixtures with catalog samples. Showing Source Operations 97 last-good as All Stocks. |

### 12.3 Prerequisites that R3–R15 still need (from new collector/UI plan)

1. **R1 DTO — done (live).** `resolve_evidence` still needs an **adapter** from those rows to `EvidenceClaim` + `NormalizedFact` + `SourceResult`. Catalog samples and snapshot lamps are not those types.  
2. **R2 attention — done (live).** R6/R8/R11/R12 stay shortlist-expensive. Running them on 123 jobs or 165 cards is still the wrong result.  
3. **Alias map.** R6/R12/R14 must use job keys / normalized families, not companion card keys.  
4. **Cadence + envelope.** 10 envelope-only sources on 2026-08-16 cannot enter R3 claims. Stale MCX last-good cannot enter R11.  
5. **`nse_index_close_eod` is still not a 123-job voter.** It is an A5 companion fetched by `reconcile_research_session`. Do not add a 124th registry row. Missing/mismatched index date is `WAIT_INDEX_CONTEXT_MISSING`, not an invented Nifty close.  
6. **Family router.** R11/R12/R6 must not call cash A1–C1.  
7. **R3 does not write public_state.** R2 BASELINE is the live list. C1 is cash attention input to R1/R2. Live R3 only attaches FUS-009 selected/suppressed diagnostics. See §13.  
8. **R5 CONFIRMED is not unlocked by UI.** Fixture CONFIRMED stays fixture. Live CONFIRMED requires File A R5 **and** R2-B activation. Workbench and radar fixture counts must not display it as live.  
9. **R15 page owner.** TrendForge command-room / FINAL_PRODUCT IA. Inventory Workbench stays collector glass. A later display ticket may *read* R1/R2/R3 DTOs; it is not R15 itself.  
10. **CAD-004 scheduler.** R9 session bars and R11/R12 “fresh” clocks fail if they assume auto collect. Manual Refresh is the only observed collect path.

### 12.4 Safe future build order (replaces “extend R3 then jump to R8”)

```text
done:   Q5 fixtures R3/R5/R7  +  cash A1–C1  +  collector 123  +  workbench glass
        + live R1 DTO + live R2 attention (post-commit)
        + live R3 WAIT-only + live R4 ID pin (zero PK vote) + live R5 WAIT-only
        + live R14 CA join WAIT-only (R4 → R14 → R5; R5 consumes the join)
next:   R6 live enrichment on R2 shortlist (extend A6, do not replace)
        R8 native scanners under family caps (not workbench screener)
        R9 lifecycle/ORB/VWAP on verified bars only
        R10 pipe DSL (zero claims) before live R11/R12
        R11 MCX only with local master; else WAIT
        R12 options timeline from last-good option jobs; no confirm
        R13 remaining scanner batches
        R15 Scanner Lab on TrendForge frontend from canonical DTOs
closed: R2-B activation, live CONFIRMED (except future R5 gate), qty, broker
never:  workbench as R15; catalog as R1; Consensus v4 as R3; /api/radar as R2
```

### 12.5 Adversarial tests before wiring R3–R15

1. `resolve_evidence` called with only catalog `records_sample` → reject / CATALOG_ONLY, no state.  
2. Companion `nse_regulation_31` + official pledge → one family, not two votes.  
3. `nse_option_chain` card vs `nse_option_chain_equity` last-good → one options root.  
4. Envelope-only last-good → cannot create R3 claim.  
5. Stale `mcx_bhavcopy` last-good → R11 WAIT, not WATCH.  
6. Q5-R3 fixture CONFIRMED is not returned by live selection or workbench.  
7. C1 and `resolve_evidence` cannot both persist a public state for the same run.  
8. R7 PK worker crash leaves A1–C1 and last-good unchanged.  
9. R15 page without R1 DTO shows explicit empty/WAIT, never fixtures as live.  
10. Workbench Source Operations still has no symbol rank after R3 is live.  
11. Missing `nse_index_close_eod` → no invented index context; R5 cannot confirm.  
12. Pipe (R10) stage count changes do not change family counts or state.

### 12.6 Honest verdict

R3–R15 **product law is still correct.** The **wiring plan was incomplete** after the new UI/collector work:

- Code for R3/R5/R6/R11/R12 exists mainly as **fixtures**.  
- Live cash path is **A1–C1**, which does not call `resolve_evidence`.  
- Command-room `/api/radar` is a **third** path.  
- Workbench is a **fourth** path and will never produce R3–R15 acceptance.  
- Building R15 or R3 against the workbench **cannot** yield File A expected results.
- R1/R2 are live. **R3 is not.** Build R3 only from **§13**.

---

## 13. LOCKED R3 build contract — execute this only (do not re-plan)

**Status:** Specified, pre-build audited, and **not started**. Section 13.9 is a
binding correction to the original contract. Do not implement before its
authority prerequisite is approved.  
**Authority:** File A §15 R3 + `FUS-009`. This section is the only R3 how-to.  
**When:** After current R1/R2 (already live). Before R4/R5/R6 live work.

### 13.0 What R3 is / is not

| R3 is | R3 is not |
|---|---|
| FUS-009: one support + one oppose per correlation group; then family max; missing family = 0 | Re-downloading 123 links |
| Attach selected/suppressed claim IDs + conflict flags to an existing R2 row | A second All-Stocks ranker |
| Live `state_ceiling=WAIT` | CONFIRMED, qty, activation, broker |
| Optional claim chips on TrendForge command-room live adapter | Workbench Consensus / Source Operations / catalog samples |

Freshness (“is the link present and not wrongly old”) stays **collector + R1**. Until a trade account exists, R3 still cannot unlock CONFIRMED.

### 13.1 Already true (do not re-verify as blockers)

- Collector: 123 jobs, aliases, last-good. SPA does not fetch NSE.
- A1–C1 post-commit live. A5/B may be SKIPPED (missing, not zero).
- R1: `GET /api/v1/selection/evidence` — `trendforge.inventory-source-bundle.v1`
- R2: `GET /api/v1/selection/attention` — BASELINE + SHADOW, `PRIMARY` forbidden
- File A R2-B = **activation, closed**. Shadow ticket name is **R2-SHADOW**
- Workbench = glass. `selection-live-adapter.js` shows R2, not FUS-009
- `resolve_evidence()` exists and is **fixture-only** (`r2_fixtures.py`, `r3_fixtures.py`)
- Q5-R3 fixture **must keep** one EOD CONFIRMED for the fixture suite. That path stays `fixture_only=true`

### 13.2 Files and functions (reuse, then add)

Reuse, do not fork:

- `selection/resolver.py` — `resolve_evidence()`, `ResolutionProfile` (`state_ceiling=WAIT`)
- `selection/contracts.py` — `EvidenceClaim`, `NormalizedFact`
- `source_contracts.py` — `SourceResult` (`is_available_at`)
- `selection/inventory_source_bundle.py` — latest R1 bundle only
- `selection/attention_order.py` — R2 BASELINE order; do not rewrite rows’ `public_state`
- `selection/cash_post_commit.py` — add one stage **after** R2 persist
- `selection/store.py` — persist R3 payload next to R1/R2 hashes
- `main.py` — read-only `GET` only; GET never builds

Add:

- `selection/r3_claim_adapter.py` — `claims_from_r1_bundle(bundle) -> (claims, facts, source_results)`
- `selection/r3_live.py` — `build_r3_resolution(bundle, attention) -> R3ResolutionV1`
- persist/latest helpers
- `GET /api/v1/selection/resolution` (bundle-scoped) and optional `.../resolution/{symbol}`
- tests: `backend/tests/test_r3_live.py` (do not weaken `test` Q5-R3 fixtures)

### 13.3 Input / output / identity

**Input (fail closed if any mismatch):** same `collectorRunId`, `cashPipelineRunId`, `r1BundleHash`, `permissionFingerprint`, `tradingDate` as latest completed R1 **and** R2. No R2 → 503 `R3_ATTENTION_NOT_READY`. No R1 → 503 `R3_EVIDENCE_NOT_READY`.

**Adapter rules:**

- One claim stream per **dataset root / correlation group**, not per catalog card
- `aliasOf` rows do not add claims
- Skip: `voteEligible=true` never (today all false); `evidenceEligible=false`; envelope; `CATALOG_ONLY`; companions; stale last-good used as fresh
- `SourceResult.is_available_at(decision_at)` must pass or the claim is suppressed (`SUPPRESSED_SOURCE_STATE`)
- Do not read `links_105.json` or workbench samples

**Output `trendforge.resolution.v1`:**

- `schemaVersion`, `runId`, `runHash`, `r1BundleHash`, `r2RunHash`, same run/date fingerprints
- `profileId` / `profileVersion` / frozen `familyWeights` (sum ≤ 1)
- `stateCeiling=WAIT`, `sourceActivationReady=false`, `canUnlockConfirmed=false`
- per symbol: `selectedSupportClaimIds`, `selectedOppositionClaimIds`, `suppressed[]` `{claimId, disposition, reason}`, `familySupport`, `familyOpposition`, `missingFamilies`, `conflict=true` if both sides selected, `evidenceStrength` labelled **not win probability**
- **no** `public_state` field that can override R1/R2
- **no** entry/target/stop/qty

**Join:** R2 `displayOrder` / `attentionPriority` unchanged. UI may *show* R3 conflict/suppression next to an R2 row.

### 13.4 Profile and A5

- Live profile: `state_ceiling=WAIT`, `allowed_data_modes` exclude using fixture CONFIRMED profile
- Missing required family (live A5 index **SKIPPED**) → that weight stays 0; **do not renormalize** remaining weights
- Conflict (support and opposition both selected in a group) → row stays WAIT; set `conflict=true`; do not CONFIRMED and do not drop the row

### 13.5 Post-commit hook

```text
existing: last-good → A1–C1 → persist R1 → persist R2 (+ shadow)
add:      if R1 and R2 completed with matching fingerprints
            → build_r3_resolution → persist
          else skip R3; keep R1/R2; do not fail the collector
GET /api/v1/selection/resolution  reads latest only
```

Idempotent on `(collectorRunId, r1BundleHash, r2RunHash, profileVersion)`. Failed R3 never replaces last good R3 and never rolls back last-good or R1/R2.

### 13.6 UI (optional in the same ticket, not required to start)

Allowed: extend `selection-live-adapter.js` to fetch resolution and show support/oppose/suppressed/conflict on an existing live row.  
Forbidden: workbench Consensus as FUS-009; Source Operations as rank; mixing Q5-R3 fixture CONFIRMED into live DOM; new score number that looks like win%.

### 13.7 Tests (must exist before claiming R3)

1. Adapter from a real-shaped R1 fixture: 123 jobs, aliases add **zero** extra claims.  
2. Catalog `records_sample` as input → reject.  
3. Envelope / `evidenceEligible=false` → no claim.  
4. Companion + official same root → one group.  
5. Skipped A5 → index family 0, weights not renormalized.  
6. Live profile cannot emit CONFIRMED.  
7. Q5-R3 fixture suite still has exactly one fixture CONFIRMED and `fixture_only=true`.  
8. R2 `public_state` and `displayOrder` unchanged after R3 persist.  
9. Mismatched fingerprints → no persist; 503 typed.  
10. GET does not compute.  
11. `evidence_strength` label present; no win%.  
12. Workbench tests still have no R3 rank API.

### 13.8 Done when

- One live resolution persisted for the same run as latest R1/R2  
- GET returns `trendforge.resolution.v1`  
- R2 list unchanged; no CONFIRMED; activation false  
- §13.7 tests pass  
- Workbench still has no symbol rank from R3  

**Not done if:** new downloader, 165-card votes, PRIMARY, workbench Consensus, or live CONFIRMED.


---

### 13.9 Binding pre-build correction - 2026-08-16

This subsection supersedes conflicting implementation detail in 13.2-13.8. The audit found that R3 is not ready to implement from the public R1 DTO alone.

| Gap | Observed evidence | Binding correction |
|---|---|---|
| R3-GAP-001 | No live R3 adapter, builder, store helper or read API exists. | R3 remains NOT STARTED. Fixture resolver behavior is not live completion evidence. |
| R3-GAP-002 | SourceEvidenceRecordV1 omits complete SourceResult and PIT lineage required by resolve_evidence(). | Consume in-memory A1 SourceResult and A2 NormalizedFact objects from run_existing_cash_pipeline(); do not reconstruct from display DTOs. |
| R3-GAP-003 | Generic R1 source rows are not symbol-linked. | Create symbol claims only by joining A2 facts through factId; never turn every registry job into a claim for every stock. |
| R3-GAP-004 | R1 datasetRootId is an artifact-instance identity, not the compiler canonical root. | Group by compiled datasetRootId, independenceFamily and correlation group; aliases/companions add no votes. |
| R3-GAP-005 | Compiler output has zero contracts with featureIds or directional permission; nse_bhavcopy_eod is UNSPECIFIED_NO_VOTE. | No selected live claim until an approved source-contract amendment grants an accepted feature and research-only directional permission. |
| R3-GAP-006 | Old text says a conflict row stays WAIT while R2 is immutable. | R3 owns resolutionState=WAIT and blocksProgression=true; never rewrite R2 state, priority or order. |
| R3-GAP-007 | Duplicate completion checks cover R1/R2 only. | Include r1BundleHash, r2RunHash and profileVersion; duplicate input must still recover missing R3. |
| R3-GAP-008 | Generic latest can be older than current R1/R2. | Return only a hash-matched resolution; otherwise R3_RESOLUTION_NOT_READY. Historical last-good cannot appear current. |

#### 13.9.1 Authority prerequisite

Meaningful live claims require a separately approved canonical source-contract change. Do not edit the workbook under this milestone. Proposed reserved contract:

- FTR-040 cash-session attention composite;
- source nse_bhavcopy_eod official EOD bhavcopy;
- inputs: current A2 fact plus R2 attention priority/direction;
- strength: deterministic attentionPriority, explicitly not probability;
- family PARTICIPATION; correlation group CG_ACTIVITY_SESSION;
- research-only directional permission;
- WATCH/WAIT ceiling; gate, quantity, execution and activation false.

Without approval, R3 may expose only suppressed/no-claim diagnostics. It cannot invent feature IDs, direction or family membership.

#### 13.9.2 Correct live adapter boundary

~~~python
claims_from_cash_pipeline(
    bundle: InventorySourceBundleV1,
    attention: AttentionOrderV1,
    staging_results: tuple[SourceResult, ...],
    identity_facts: tuple[NormalizedFact, ...],
    compiled_source_contracts: tuple[CompiledSourceContract, ...],
    decision_at: datetime,  # exactly attention.builtAt
) -> ClaimAdapterResult
~~~

R1 may add stagingResultId and identityBatchId for observability; they do not replace exact objects. Decision time is R2 builtAt, never wall clock.

#### 13.9.3 Frozen live profile

- PRF-R3-LIVE-DIAGNOSTIC v1.0.0;
- stateCeiling WAIT; sourceActivationReady false;
- required source nse_bhavcopy_eod;
- required families STRUCTURE and PARTICIPATION;
- weights: safety .20, market .15, structure .30, participation .25, event .10;
- missing weights stay zero and are never renormalized;
- A5/A6 completion alone is not evidence;
- live result remains WAIT until accepted claims back required families.

#### 13.9.4 Output, API and recovery

Persist trendforge.resolution.v1 with exact R1/R2 hashes, profile, decision time, selected/suppressed IDs, family support/opposition, missing families, conflict, resolutionState, blocksProgression and typed reasons. It cannot override R2.

GET /api/v1/selection/resolution is read-only and hash scoped: 200 only for current matching data; otherwise typed 503. Failed R3 preserves current matching data. Duplicate R1/R2 completion must not suppress missing-R3 recovery.

#### 13.9.5 Additional acceptance tests

1. Exact A1/A2 objects feed adapter; DTO reconstruction rejected.
2. No joined factId means no symbol claim.
3. Artifact-instance IDs cannot be correlation roots.
4. Missing feature/directional permission suppresses claim.
5. Aliases/companions cannot increase family support.
6. decision_at equals R2 builtAt; replay deterministic.
7. Duplicate input recovers missing R3.
8. Hash-mismatched R3 cannot be current.
9. Conflict sets R3 WAIT/block and leaves R2 bytes unchanged.
10. Missing-family weights remain zero without renormalization.
11. No selected claim before authority approval.
12. After approval, one bhavcopy fact creates at most one participation claim.
13. GET never computes or mutates.
14. Failed R3 preserves current matching artifact.
15. Fixture CONFIRMED cannot enter live storage/API.
16. No trade geometry, quantity, probability or broker fields.
17. Activation false caps live R3 at WAIT.
18. Workbench and records_sample inputs rejected.

#### 13.9.6 Corrected gates

**Start only when:** authority prerequisite approved, compiler proves feature/family/directional contract, and exact A1/A2 objects are available post-commit. Otherwise stop at diagnostic plumbing.

**Done only when:** 13.7 and 13.9.5 pass, runtime has a hash-matched persisted/API artifact, R2 bytes are unchanged, and live R3 emits no CONFIRMED. Fixtures alone are insufficient.


---

## 14. R1/R2 cadence closure - 2026-08-16

This observed closure supersedes the planning-only runtime statements in the
earlier cadence section. It does not change File A sequence or authorize R3.

- Existing registry rules now drive R1 freshness under policy
  `registry-cadence-v1`; no second freshness registry or downloader was added.
- R1 exposes cadence, publication, active-window, holiday/closed-day,
  empty-data, expected-session and typed freshness evidence through additive v1
  fields. Stale, future and temporally unknown rows are visible but ineligible.
- R2 consumes the same R1 contract. `STALE_DATA` becomes WAIT/no rank and cannot
  produce CONFIRMED or trade geometry.
- The A1-C1 post-commit fingerprint includes the policy version, preventing a
  completed older policy from suppressing the required rebuild.
- Observed full refresh: 123 attempted, 119 new-data success, 1 stale last-good,
  3 valid-empty, 0 failed.
- Observed R1: 123 sources, 2,463 stocks; 94 CURRENT, 11 STALE, 18 UNKNOWN.
- Observed R2: 1,720 WATCH, 743 WAIT, 0 CONFIRMED, 0 ranked non-current rows and
  0 populated entry/target/stop geometry.
- Verification: 29 focused tests, 905 complete backend tests and 161/161
  frontend checks passed. The sole backend warning is the existing
  Starlette/httpx deprecation.

R1 and R2 are complete at the research-only WATCH/WAIT/REJECT ceiling. Registry
cadence evidence remains provisional and source activation remains false.
**Next milestone: R3 evidence-family resolution in section 13; not started.**

### 13.10 R3 implementation record - 2026-08-16

R3 is implemented under the §13.9 binding correction. FTR-040 is the sole reviewed live directional feature contract: closed NSE EOD cash participation, `CG_ACTIVITY_SESSION`, SWING/NSE_EQ, WAIT-only. `r3_claim_adapter.py` joins exact A1/A2 lineage; `r3_live.py` applies FUS-009 through the existing resolver; `cash_post_commit.py` persists and recovers R3 after immutable R1/R2; `GET /api/v1/selection/resolution` is read-only and hash scoped.

Observed saved-artifact replay produced 2,463 R3 rows, all WAIT, with 2,437 selected participation claims, 0 conflicts, 0 CONFIRMED and no trade geometry or quantity. The pre-FTR-040 R1 fingerprint was rejected until R1/R2 rebuilt under the current compiler contract. Source activation and gate authorization remain false. This closes R3 only; it does not authorize R5 CONFIRMED or add intraday/MCX/options/event contracts.

### 13.12 R4 implementation record - 2026-08-19

Live R4 is the File A PK0 pin plus explicit ID inventory overlay. `r4_live.py` binds current R1/R2 hashes to A2 `instrument_id` values, refuses companion scrip codes, stores the pinned PK inventory digest, and never votes. `GET /api/v1/selection/identity-pin` is read-only and hash-scoped. Cash post-commit runs R4 after R3 and before R5. R5 does not consume R4. `r4_fixtures.py` stays the Q5-R4 enrichment/MCX/options fixture.

This does not authorize CONFIRMED, expand FTR-040, or start R7 PK runtime.

### 13.13 Hybrid S4/S5 paper A/B overlay - 2026-08-21

Not a File A milestone. Do not treat this as R6–R13 or as live CONFIRMED.

`GET /api/v1/selection/s4s5-compare` computes both original compressed S4/S5 (`p̂` mixes B1–B5; wall votes as entry) and the split family (`p̂` from B1–B3 proxy; B4 package; B5 location) on current R1/R2 hashes. Frontend `#s4s5ComparePanel` checkboxes are WITH original S4/S5, WITHOUT split, and BOTH. Calibration is `RESEARCH_PROXY_NOT_CALIBRATED`. Rows stay WAIT. Kelly is illustration, not size.

**New files (not File A stages):**
- `backend/trendforge_api/selection/s4s5_compare.py` — formula A/B
- `backend/tests/test_s4s5_compare.py` — wait-only + WITH p̂ > WITHOUT p̂
- `frontend/s4s5-compare.js` — WITH / WITHOUT / BOTH checkboxes

**Wired into existing files:** `backend/trendforge_api/main.py` (GET route), `frontend/index.html` (`#s4s5ComparePanel`), `frontend/styles.css`, `frontend/tests/acceptance-check.js`.

Both formula families stay until paper days decide which to keep. Do not delete either family. Do not paste either family into `r5_live.py` until that pick plus R14 + R2-B.

### 13.14 R14 implementation record - 2026-08-21

Built from `docs/fable/remaining_build/R14_LIVE_CA_JOIN_GLM_PROMPT.md`. Live R14 is the official corporate-action / identity-continuity join at `LIVE_CA_JOIN_WAIT_ONLY`: `selection/r14_live.py` binds each R2 row through the R4 A2 `instrument_id` pin to DAT-022-reconciled official observations (`nse_corporate_filings_actions`, already job `CA_SOURCE`; 123 jobs unchanged), plus any A4 `cash_ca_vintages` rows as additional reconciliation inputs (conflict if terms disagree). `corporate_actions.reconcile_corporate_actions` is reused verbatim; `ALGORITHM_VERSION=DAT-022-v1` pins the factor set (split `den/num`, bonus `den/(num+den)`, dividend `(P-c)/P` on full OHLC, rights TERP, merger/demerger only with explicit factor + same-symbol continuity). Replay at `decision_at` drops observations with `parsed_at`/`available_at > decision_at` and counts them in `hiddenFutureEventCount`. Cross-symbol predecessor/successor without same-instrument proof is `IDENTITY_BREAK`; `UNKNOWN_ID` / `COMPANION_REJECTED` rows never join CA onto a scrip code. Row states are WAIT/REJECT only; validators forbid CONFIRMED, vote, rank, unlock and trade geometry; `WAIT_CA` cannot carry a factor version; adjusted series open only through `series_layers.open_adjusted_series` keyed by `factor_version` (STO-020: RAW bars never mutate).

Persistence and API clone R4/R5: `persist_selection_payload` under profile `PRF-R14-CA-JOIN`, `GET /api/v1/selection/ca-join` (+ `/{symbol}`) read-only and hash-scoped to current R1/R2 (+ R4 pin) — mismatch is 503 `R14_CA_JOIN_NOT_READY`, never silent last-good; unknown symbol 404; POST 405. `cash_post_commit.py` runs the stage order `R3 → R4 → R14 → R5` under `PIPELINE_VERSION a1-c1-r1-r2-r3-r4-r14-r5-orchestrator-7` and carries `r14_join_id` on the execution/run; if R14 fails, R5 is `BLOCKED` with `WAIT_R14_JOIN_NOT_READY` instead of falling back to raw vintages.

R5 consumes the join as its only CA authority: `build_r5_structure_batch` requires a hash-matched R14 batch (R1/R2 hashes, plus the current R4 pin hash when present) else `WAIT_R5_R14_JOIN_NOT_READY`; per symbol `ca_state` `NONE` keeps the no-CA path, `ADJUSTED` applies the joined DAT-022 factors to pre-ex OHLC (volume divides only for SPLIT/BONUS), and `WAIT_CA` returns no bars with `WAIT_CA_CONFLICT` / `WAIT_CA_IDENTITY_BREAK` / `WAIT_CA_WAIT_DETAILS` / `WAIT_CA_UNRESOLVED` gates and empty `claim_ids`. The R5 batch carries `r14RunId` / `r14RunHash` (GET /structure proves join lineage; hash miss is 503 `R5_R14_JOIN_NOT_READY`), and a newly visible CA changes `factor_version`, therefore the adjusted series id and both run hashes — a previous JOINED run is never reused (T-113). `confirmedCount=0` everywhere; Hybrid S4/S5 stays overlay-only.

Tests: `backend/tests/test_r14_live_ca_join.py` (22 cases: T-013/096/096b/097/097b/098/099/113/178, PIT hiding, conflict, cancelled, identity break, UNKNOWN_ID, companion scrip, lineage fail-closed, ceiling validators, hash-scoped GET + POST 405, R5 consume lineage) plus the §11 six-file verification command — 62 passed. This closes R14 WAIT-only only: R6 sponsor votes, R2-B activation, live CONFIRMED and qty remain closed.

### 13.11 Current R1-R3 debugging handoff - 2026-08-17

Use this as the live-selection checkpoint before R4. It describes the saved-data
path only; it does not modify File A order or authorize a trade.

| Stage | Job | Current proof | Must remain false |
|---|---|---|---|
| R1 | Qualify saved source evidence by schema, lineage and each source's cadence | `trendforge.inventory-source-bundle.v1`; 123 source contracts and 2,463 stock rows | HTTP 200 alone is not usable data; stale, malformed, envelope-only and unknown-time data cannot become eligible evidence |
| R2 | Preserve the immutable BASELINE attention order over R1/A1-C1 results | `trendforge.inventory-discovery.v1`; 1,720 WATCH and 743 WAIT in the observed replay | R2 is not a trade recommendation; stale/unknown rows do not rank; no CONFIRMED or entry/target/stop/quantity fields |
| R3 | Resolve evidence families without double counting correlated claims | `trendforge.resolution.v1`; exact A1/A2 and R1/R2/compiler hash match; FTR-040 allows one NSE EOD PARTICIPATION claim per stock/correlation group | R3 cannot rewrite R2 state/order, activate a source, unlock CONFIRMED, or produce broker/execution fields |

Debug in this order: confirm matching collector, R1 and R2 hashes; check the
compiler permission fingerprint; then inspect the R3 selected, suppressed,
missing and conflict fields. A mismatch returns the typed R3 not-ready response;
a GET request never rebuilds evidence. The Inventory Workbench remains source
health glass and is not an input to any of these stages.

**R14 official CA join is implemented WAIT-only (§13.14); R5 consumes it.** Live CONFIRMED still requires R2-B plus a separate File A amendment. R4/R14 must not expand FTR-040 or silently
make intraday, MCX, options or event evidence directional. Next code milestone: R6.
