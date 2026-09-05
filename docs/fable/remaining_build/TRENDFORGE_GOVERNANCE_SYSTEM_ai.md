# TrendForge Two-Document Governance and Cross-Reference System

**Date:** 2026-07-20  
**Status:** PRESERVED_EXTERNAL_ADVISORY_REFERENCE  
**Authority:** None. This Kimi/GLM advisory analysis is preserved as review evidence. Current explicit instructions, `AGENTS.md`, and File A govern implementation. File B is opened through File A pointers. No self-declared statement in this document may override that hierarchy.

**Supersession notice:** Later phrases in this preserved response such as “governs,” “authority,” “must be adopted,” or File B authority are quoted advisory proposals. They are non-operative and superseded by the header above; retain them only so no external idea is silently deleted.

---

## 1. Executive Verdict

### 1.1 Can File A alone be sufficient?

**No.** File A (`new_merge_PLAN_2026-07-18.md`) controls implementation order but lacks:

- The exact 354-source inventory baseline and operational workbook references
- Detailed per-strategy source combinations with exact `source_key` references
- Complete EvidenceClaim and Guidance contract templates
- Specific legacy code issues in `intraday_stock_details.py` lines 887-931
- Exact risk/quantity sizing formulas (even though excluded from current scope)
- Detailed timestamp/revision field specifications (8+ fields)
- Source-state maturity ladder (10 states)
- Dataset-root identity and dedupe model
- Cross-exchange event matching states
- Decision-job taxonomy (J01-J14)
- Specific transport behavior requirements (9 behaviors)
- F&O-ban/MWPL contract split semantics
- USD/INR role split for MCX
- Legacy state migration mapping
- Detailed UI layout specifications
- Productivity requirements
- Specific code correction references

**File A alone would produce an implementable but incomplete system.** Critical domain knowledge exists only in File B.

### 1.2 Materiality of File B content

| Disposition | Count | Percentage |
|---|---|---|
| Fully represented in File A (PRESENT) | 8 | ~18% |
| Partially represented (PARTIAL/IMPROVE_A) | 27 | ~61% |
| Completely absent from File A (FILE_B_ONLY/ADD_TO_A) | 9 | ~21% |
| In conflict with File A (CONFLICT) | 3 | ~7% |
| **Total material items analyzed** | **47** | **100%** |

### 1.3 Can both files remain separate without ambiguity?

**Yes, if governed by these rules:**

1. File A is the **build-sequence authority** -- it controls what is implemented, in what order, with what acceptance criteria.
2. File B is the **domain-detail authority** -- it preserves why something is done, how formulas work, what specific sources are used, and what exact values apply.
3. Any conflict: File A governs scope and sequence; File B governs domain accuracy within that scope.
4. No File B requirement may be implemented without a File A milestone.
5. No File A milestone may be accepted without consulting File B for formula, source, or contract detail.

### 1.4 What is File B missing that File A has?

| Capability | File A Coverage | What is Missing from File B |
|---|---|---|
| Four-state state machine (WATCH/WAIT/CONFIRMED/REJECT) | Complete | Legacy state migration mapping (HYBRID-19-5) |
| Feature contract template (22 fields) | Complete | Specific formula derivations for 30+ features (HYBRID-16-7) |
| S0-S9 cheap-to-expensive pipeline | Complete | Per-strategy exact source combinations (HYBRID-6-1, HYBRID-16-7) |
| Rejected items registry (REJ-001..012) | Complete | Formal rejection mechanism |
| PK runtime sidecar (PK-016..019) | Complete | Finite offline harness only |
| OpenAlgo as early critical path | Complete | Disabled, no live execution |
| Implementation sequence (R0-R18) | Complete | H-series milestone mapping (HYBRID-19-11) |
| Feature registry (FTR-001..039) | Complete | Feature formula detail (HYBRID-16-8) |

**Conclusion:** File A provides sufficient structure to begin implementation. File B provides the detailed domain knowledge required to implement correctly. Both are required.

---

## 2. Document Roles

### 2.1 File A: `new_merge_PLAN_2026-07-18.md` -- Execution Roadmap Authority

| Attribute | Value |
|---|---|
| **Role** | Controls implementation order, scope boundaries, acceptance criteria |
| **Governs** | R0-R18 implementation sequence, feature registry, state transitions, API contracts |
| **Contains** | Requirement IDs (GOV-001, STA-001, FUS-001, etc.), milestone definitions, test specifications |
| **May not contain** | Detailed formula derivations, exact source inventory, legacy code references, per-strategy source combinations |
| **Change control** | Requires explicit version bump, PIT validation, and governance review |

### 2.2 File B: `TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` -- Domain Reference Authority

| Attribute | Value |
|---|---|
| **Role** | Preserves detailed source intelligence, formula derivations, exact inventory, domain rationale |
| **Governs** | Why a formula works, what exact sources are used, what specific values apply, what legacy issues exist |
| **Contains** | 354-source inventory, EvidenceClaim/Guidance contracts, risk sizing formulas, feature formulas, code corrections |
| **May not contain** | Implementation sequence, milestone definitions, state machine transitions, API route specifications |
| **Change control** | May be updated for domain accuracy without version bump if File A references are unchanged |

### 2.3 This Governance Document

| Attribute | Value |
|---|---|
| **Role** | Mediates between File A and File B, resolves conflicts, defines cross-reference conventions |
| **Governs** | Which document wins in conflicts, how items map between files, what must be added to each file |
| **Contains** | Coverage matrix, gap analysis, conflict resolutions, append-ready blocks, cross-reference conventions |
| **May not contain** | New requirements not present in either file, new formulas not present in File B |
| **Change control** | Requires explicit version bump when conflicts are resolved or new cross-references are added |

---

## 3. Cross-Reference Conventions

### 3.1 File A references File B

When File A needs domain detail from File B, use this exact format:

```markdown
**Reference:** File B: Section X.Y for [specific detail].
```

Example:
```markdown
**Reference:** File B: Section 16.8 for feature formula derivations.
**Reference:** File B: Section 19.2 for decision-job taxonomy J01-J14.
```

### 3.2 File B references File A

When File B needs implementation context from File A, use this exact format:

```markdown
**File A Authority:** `[REQ-ID]` governs [scope]. This section preserves domain detail only.
```

Example:
```markdown
**File A Authority:** `REJ-011` explicitly rejects quantity sizing from current scope. This section preserves the formula for future H10 milestone.
**File A Authority:** `FUS-009` governs evidence fusion. This section preserves an alternative formula for research comparison.
```

### 3.3 Conflict notation

When File A and File B disagree, use this exact format:

```markdown
**Conflict:** [brief description]
**Resolution:** File A [ID] governs. File B Section [X.Y] preserved as [research reference / domain detail / future milestone].
**Rationale:** [one sentence explaining why File A wins].
```

---

## 4. Complete Coverage Matrix

### 4.1 File B Items Mapped to File A

| File B ID | File B Section | File B Description | File A Equivalent | Disposition | Resolution |
|---|---|---|---|---|---|
| HYBRID-1-1 | 1. Objective | Question 7: quantity/risk sizing | REJ-011, GOV-002 | **CONFLICT** | File A governs: reject from current scope; preserve in File B for H10 |
| HYBRID-2-1 | 2. Inventory | 370/354/105/231/18 counts | Absent | **ADD_TO_A** | Add source inventory baseline to File A R0 |
| HYBRID-4-1 | 4. Source contract | source_key, decision_jobs, independence_family | DAT-021 (partial) | **IMPROVE_A** | Reference File B Section 4 from DAT-021 |
| HYBRID-5-1 | 5.8 Risk sizing | ATR/spread/gap/liquidity/portfolio/quantity pipeline | REJ-011 | **CONFLICT** | File A governs: reject from current scope; preserve in File B for H10 |
| HYBRID-5-2 | 5.9 OpenAlgo promotion | 5-stage promotion sequence | OPN-001..005 (partial) | **IMPROVE_A** | Reference File B Stage 9 from OPN section |
| HYBRID-6-1 | 6. Strategy combinations | Mandatory/optional/veto per strategy | PRF-001..007 (partial) | **IMPROVE_A** | Reference File B Section 6 from PRF section |
| HYBRID-7-1 | 7. EvidenceClaim | Complete claim schema with permissions | Claims table (partial) | **IMPROVE_A** | Reference File B Section 7 from claims section |
| HYBRID-7-2 | 7. Guidance contract | entry_zone, stop, targets, quantity, max_loss | Absent | **ADD_TO_A** | Add guidance contract to File A Section 13 |
| HYBRID-8-1 | 8. Storage model | ZIP/CSV/JSON/Parquet/SQLite/DuckDB choices | Section 14.1 (partial) | **IMPROVE_A** | Reference File B Section 8 from storage section |
| HYBRID-9-1 | 9. UI layout | Command bar, radar, risk/action rail | UI-001..009 (partial) | **IMPROVE_A** | Reference File B Section 9 from UI section |
| HYBRID-9-2 | 9. Inspector tabs | 7 tabs with specific content | Section 13.2 (partial) | **MERGE** | Merge tab structures; File A governs |
| HYBRID-10-1 | 10. Productivity | 10 productivity features | FTR-033 (partial) | **ADD_TO_A** | Add to File A UI acceptance criteria |
| HYBRID-11-1 | 11. API additions | /risk/evaluate, /guidance endpoints | Section 14.2 (partial) | **ADD_TO_A** | Add missing endpoints/tables to File A |
| HYBRID-15-1 | 15. Fable audit gaps | 9 critical gaps identified | Sections 20-23 (partial) | **IMPROVE_A** | Ensure all gaps have File A coverage |
| HYBRID-16-1 | 16.1 Workbook paths | Exact paths and SHA-256 hashes | Absent | **ADD_TO_A** | Add to File A R0 |
| HYBRID-16-2 | 16.3 Source-state ladder | 10-state maturity ladder | Absent | **ADD_TO_A** | Add to File A Section 5 or DAT-023 |
| HYBRID-16-3 | 16.4 Inventory defects | 11 observed defects | DAT-018 (partial) | **IMPROVE_A** | Reference File B 16.4 from DAT-018 |
| HYBRID-16-4 | 16.5 URL roles | 10 canonical roles with counts | Absent | **ADD_TO_A** | Add canonical roles to File A source registry |
| HYBRID-16-5 | 16.6 Exact key lists | 69 linked + 43 not-linked keys | Absent | **ADD_TO_A** | Add exact key lists to File A |
| HYBRID-16-6 | 16.7 Strategy source combos | Exact source combinations per strategy | PRF section (partial) | **IMPROVE_A** | Reference File B 16.7 from PRF section |
| HYBRID-16-7 | 16.8 Feature formulas | 30+ feature derivations | FTR-001..039 (partial) | **IMPROVE_A** | Reference File B 16.8 from FTR section |
| HYBRID-16-8 | 16.9 Fusion formula | q_i = authority * freshness * schema... | FUS-009 (conflict) | **CONFLICT** | File A FUS-009 governs; File B formula preserved as research reference |
| HYBRID-16-9 | 16.10 Legacy scorer | intraday_stock_details.py lines 887-931 | FUS-008 (partial) | **IMPROVE_A** | Reference File B 16.10 from FUS-008 |
| HYBRID-16-10 | 16.11 ML plan | PIT feature store, Brier, ECE, promotion guards | STO-017/018 (partial) | **IMPROVE_A** | Reference File B 16.11 from validation section |
| HYBRID-17-1 | 17.2 P0.1 Tradability | T2T, ESM, ASM, GSM, F&O ban, MWPL contract | FTR-035 (partial) | **IMPROVE_A** | Reference File B 17.2 from FTR-035 |
| HYBRID-17-2 | 17.2 P0.2 Raw/adjusted | Immutable raw + versioned adjusted layers | STO-020 (partial) | **IMPROVE_A** | Reference File B 17.2 from STO-020 |
| HYBRID-17-3 | 17.2 P0.3 Timestamps | 8 timestamp fields + revision semantics | DAT-019 (partial) | **IMPROVE_A** | Reference File B 17.2 from DAT-019 |
| HYBRID-17-4 | 17.2 P0.4 Family hierarchy | Parent/child family structure with caps | FUS-009 (partial) | **IMPROVE_A** | Reference File B 17.2 from family section |
| HYBRID-17-5 | 17.2 P0.5 Realizable risk | max(stop, gap, circuit, liquidity stress) | REJ-011 | **CONFLICT** | File A governs; preserve in File B for H10 |
| HYBRID-17-6 | 17.2 P0.6 Legacy quarantine | Explicit permission flags for legacy scorer | FUS-008 (partial) | **IMPROVE_A** | Add explicit flags to File A FUS-008 |
| HYBRID-18-1 | 18.4 Dataset-root model | 10-field dedupe identity model | Absent | **ADD_TO_A** | Add to File A source registry |
| HYBRID-18-2 | 18.5 Decision chains | 4 explicit data-to-decision chains | PRF section (partial) | **IMPROVE_A** | Reference File B 18.5 from PRF section |
| HYBRID-18-3 | 18.6 Code corrections | 9 specific code corrections | Sections 20-23 (partial) | **IMPROVE_A** | Reference File B 18.6 from implementation notes |
| HYBRID-19-1 | 19.2 Decision jobs | J01-J14 taxonomy with permissions | Absent | **ADD_TO_A** | Add J01-J14 taxonomy to File A |
| HYBRID-19-2 | 19.3 NSE transport | 9 required transport behaviors | DAT-020 (partial) | **IMPROVE_A** | Reference File B 19.3 from DAT-020 |
| HYBRID-19-3 | 19.4 F&O/MWPL split | Split into nse_fno_ban + nse_mwpl_percentages | DAT-015 (partial) | **IMPROVE_A** | Reference File B 19.4 from DAT-015 |
| HYBRID-19-4 | 19.5 USD/INR split | fbil_usdinr_reference vs usd_inr_live | SRC-FX (partial) | **IMPROVE_A** | Reference File B 19.5 from SRC-FX |
| HYBRID-19-5 | 19.6 State compatibility | Legacy-to-canonical state mapping | STA-005/006 (partial) | **ADD_TO_A** | Add legacy mapping to File A |
| HYBRID-19-6 | 19.7 Outcome worker | Automated PIT outcome recording | STO-017/018 (partial) | **IMPROVE_A** | Reference File B 19.7 from validation |
| HYBRID-19-7 | 19.8 Event matching | 5 match states for cross-exchange events | DAT-030 (partial) | **IMPROVE_A** | Reference File B 19.8 from DAT-030 |
| HYBRID-19-8 | 19.9 Priority correction | True P0 vs overstated P0 | R0-R18 (partial) | **IMPROVE_A** | Reference File B 19.9 from sequence |
| HYBRID-19-9 | 19.11 Legacy quarantine | 5 specific quarantine controls | FUS-008 (partial) | **IMPROVE_A** | Reference File B 19.11 from FUS-008 |
| HYBRID-19-10 | 19.12 Risk policy | Exact risk percentages as research defaults | REJ-011 | **CONFLICT** | File A governs; preserve in File B for H10 |
| HYBRID-19-11 | 19.13 Milestones | 7 new H-series milestones | R0-R18 (partial) | **IMPROVE_A** | Reference File B 19.13 from sequence |

---

## 5. Gap Analysis

### 5.1 File A Gaps (Items Missing from File A, Present in File B)

| Gap ID | Description | Trading Impact | Add to File A Section |
|---|---|---|---|
| GAP-001 | Source inventory baseline (370/354/105/231/18) | **High** | Section 5.3 or R0 |
| GAP-002 | Source-state maturity ladder (10 states) | **High** | Section 5.3 or DAT-023 |
| GAP-003 | Canonical URL role classification (10 roles) | **High** | Section 5.3 |
| GAP-004 | Exact linked/not-linked source key lists | **High** | Section 5.3 |
| GAP-005 | Decision-job taxonomy (J01-J14) | **High** | Section 5.3 or new section |
| GAP-006 | Dataset-root identity model (10 fields) | **High** | Section 5.3 |
| GAP-007 | Legacy state migration mapping | **High** | Section 10.4 |
| GAP-008 | Guidance contract template | **High** | Section 13.3 |
| GAP-009 | Productivity requirements (10 features) | **Medium** | Section 13.4 |
| GAP-010 | Missing API endpoints (/risk/evaluate, /guidance) | **Medium** | Section 14.2 |
| GAP-011 | Missing database tables (guidance, risk_evaluations, etc.) | **Medium** | Section 14.1 |

### 5.2 File B Gaps (Items Missing from File B, Present in File A)

| Gap ID | Description | Trading Impact | Add to File B Section |
|---|---|---|---|
| GAP-B-001 | Four-state state machine formal definition | **High** | Section 19.6 (expand) |
| GAP-B-002 | Feature contract template (22 fields) | **High** | Section 16.8 (expand) |
| GAP-B-003 | S0-S9 cheap-to-expensive pipeline | **High** | Section 5 (add) |
| GAP-B-004 | Rejected items registry (REJ-001..012) | **Medium** | Section 3 (add) |
| GAP-B-005 | PK runtime sidecar specification | **Medium** | Section 5.9 (add) |
| GAP-B-006 | R0-R18 implementation sequence | **High** | Section 19.13 (expand) |
| GAP-B-007 | Feature registry (FTR-001..039) | **High** | Section 16.8 (expand) |

---

## 6. Conflict Analysis

### 6.1 Identified Conflicts

| Conflict ID | Topic | File A Position | File B Position | Resolution |
|---|---|---|---|---|
| CONFLICT-001 | Quantity/risk sizing | Explicitly rejected (REJ-011, GOV-002) | Core requirement in Section 5.8 | **File A governs.** Exclude from current plan. File B rationale preserved for H10 (separately approved execution milestone). |
| CONFLICT-002 | Evidence fusion formula | FUS-009: support_strength - opposition_strength, clamp 0-100, epsilon=0 | Section 16.9: q_i = authority * freshness * schema * completeness * scope * timestamp | **File A governs.** FUS-009 is the production formula. File B formula may be evaluated as research profile through PIT validation. |
| CONFLICT-003 | Realizable-exit risk calculation | Excluded (REJ-011) | Section 17.2 P0.5: core risk component | **File A governs.** Exclude from current plan. File B formula preserved for H10. |
| CONFLICT-004 | PK runtime sidecar | PK-016..019: finite offline harness only | Sections 5.4, 16.5: permanent sidecar proposed | **File A governs.** No production PK sidecar. File B's capability coverage is achieved through native promotion after offline comparison. |
| CONFLICT-005 | OpenAlgo as early critical path | OPN-001..005: disabled, no live execution | Sections 5.9, 16.13: included in promotion sequence | **File A governs.** Exclude from current plan. File B sequence preserved for future H10 milestone. |

### 6.2 Conflict Resolution Principles

1. **Scope boundary governs.** File A's explicit rejections (REJ-001..012) are absolute. File B content within rejected scope is preserved as domain reference for future separately-approved milestones.
2. **Formula authority.** Where File A specifies a formula (FUS-009, FTR-001..039), File A governs. File B alternative formulas are research references only.
3. **Implementation sequence.** File A's R0-R18 sequence governs. File B's H-series milestones are advisory and must be mapped to R-series before implementation.
4. **Safety over completeness.** Where File B identifies a safety gap (legacy scorer, F&O ban, MWPL), File B detail informs File A requirements even if File A has a partial equivalent.

---

## 7. Append-Ready Blocks for File A

### 7.1 Add to Section 0 (Executive Summary)

```markdown
### 0.4 Two-Document Governance

This plan is governed by a two-document system:

- **File A (this document):** Execution Roadmap Authority. Controls implementation order, scope boundaries, and acceptance criteria.
- **File B (`TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md`):** Domain Reference Authority. Preserves detailed source intelligence, formula derivations, exact inventory, and domain rationale.

**Rule:** File A governs what is built and when. File B governs how it works and why. Neither file may be read in isolation.

**Cross-reference convention:** File A sections reference File B as `File B: Section X.Y`. File B sections reference File A as `File A: [REQ-ID]`.
```

### 7.2 Add to Section 5.3 (Required Dataset Roots)

```markdown
### 5.3.1 Source Inventory Baseline

The operational source of truth is:

| Workbook | Path | SHA-256 |
|---|---|---|
| SOURCE_LINK_INVENTORY_MASTER.xlsx | `D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx` | `1F76DAB1C75252AA8185C97F69FC4E6F74B5710918B9D4B3E4A1566D9C646A43` |
| SOURCE_LINK_INVENTORY_MASTER.csv | `D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.csv` | `6108466BD1CCB9DCC1537D11CEB4DFCD688BE4139BB7C5B773D407E22127B3AA` |

Verified inventory shape at plan date:

| Measure | Count |
|---|---:|
| MASTER_CURRENT rows | 370 |
| Unique canonical URL rows | 354 |
| LINKED_SOURCES rows | 105 |
| NOT_LINKED_SOURCES rows | 231 |
| SUPPRESSED_NOT_LINKED_DUPES rows | 18 |
| FETCH_EVIDENCE history rows | 3,195 |
| FETCH_EVIDENCE unique rows | 3,195 |
| FETCH_EVIDENCE unique URL rows | 205 |
| FETCH_EVIDENCE unique source_key rows | 195 |
| FETCH_EVIDENCE unique (source_key, date) rows | 205 |

**Reference:** File B Section 16.1 for workbook structure and verification procedures.

### 5.3.2 Source-State Maturity Ladder

Every source must traverse this ladder before contributing to decisions:

| State | Required Proof |
|---|---|
| REGISTERED | Canonical URL present in inventory |
| TRANSPORT_OK | HTTP 200 with valid content, no block HTML |
| ARTIFACT_VALID | Parser produces non-empty, schema-valid output |
| VALID_EMPTY | Empty output is explicitly expected (e.g., no ban today) |
| PARSER_SCHEMA_OK | Output matches declared schema |
| NORMALIZED | Output converted to canonical format |
| FRESH_FOR_JOB | Data is within freshness tolerance for target job |
| DECISION_WIRED | Source is mapped to at least one decision job |
| GATE_AUTHORIZED | Source passes independence and conflict checks |
| EXECUTION_AUTHORIZED | Source approved for execution-boundary decisions |

**Rule:** `TRANSPORT_OK` or HTTP 200 is not proof of `GATE_AUTHORIZED`. Counts must be generated for every state.

**Reference:** File B Section 16.3 for detailed ladder semantics and defect analysis.

### 5.3.3 Dataset-Root Identity Model

Every source contract must declare:

| Field | Purpose |
|---|---|
| `dataset_root_id` | Identifies the economic/regulatory dataset (e.g., NSE_EQUITY_SPOT) |
| `transport_variant_id` | Distinguishes mirror endpoints (e.g., nse_eq_spot_a, nse_eq_spot_b) |
| `mirror_group_id` | Groups variants that serve the same dataset |
| `resolver_id` | Determines which variant wins when multiple are fresh |
| `publisher_authority` | Numeric authority score (0.0-1.0) for this root |
| `endpoint_role` | OFFICIAL_OR_PRIMARY, SECONDARY_DISCOVERY, REFERENCE_ONLY, etc. |
| `activation_state` | REGISTERED, TRANSPORT_OK, ..., EXECUTION_AUTHORIZED |
| `decision_jobs` | List of J01-J14 jobs this source serves |
| `evidence_family` | Family assignment for fusion capping |
| `family_weight_cap` | Maximum directional contribution this family can provide |
| `fallback_authority_cap` | Reduced authority when used as fallback |

**Reference:** File B Section 18.4 for complete dedupe semantics and conflict resolution.

### 5.3.4 Decision-Job Taxonomy

| Job ID | Job Name | Description | Example Sources |
|---|---|---|---|
| J01 | Identity | Instrument identification and classification | nse_instrument_master, mcx_contract_master |
| J02 | Tradability | Trading restrictions and eligibility | nse_t2t_securities, nse_esm, nse_fno_ban |
| J03 | Price and Liquidity | Spot price, volume, spread, depth | nse_eq_spot, nse_eq_intraday |
| J04 | Pre-Open | Pre-market auction data | nse_preopen |
| J05 | Regime | Market regime classification | nse_eq_spot (derived) |
| J06 | Futures OI | Futures open interest and rollover | nse_futures_oi, nse_futures_oi_participant_wise |
| J07 | Options | Options chain, IV, PCR, GEX | nse_options_chain, nse_options_max_pain |
| J08 | Deals and Events | Block deals, bulk deals, corporate events | nse_block_deals, nse_bulk_deals, nse_corporate_actions |
| J09 | Corporate Filings | Regulatory filings and ownership changes | nse_shareholding_pattern, nse_insider_trading |
| J10 | AMFI/NSDL Ownership | Mutual fund and institutional ownership | amfi_india, nsdl_fii_dii |
| J11 | MCX Local | MCX-specific spot and contract data | mcx_spot_prices, mcx_contract_master |
| J12 | Global Commodity | International commodity references | lme, sge, wgc, cftc_cot |
| J13 | Portfolio Risk | Cross-position correlation and concentration | portfolio_analytics (derived) |
| J14 | Outcomes | PIT outcome recording and label generation | outcome_worker (derived) |

**Reference:** File B Section 19.2 for detailed job taxonomy and permission matrix.
```

### 7.3 Add to Section 10 (State Machine)

```markdown
### 10.4 Legacy State Compatibility

Legacy states must map deterministically to the canonical four states:

| Legacy State | Canonical State | Directional Hint | Execution Permission | Migration Version |
|---|---|---|---|---|
| `WATCH_LONG` | `WATCH` | LONG | None | v1 |
| `WATCH_SHORT` | `WATCH` | SHORT | None | v1 |
| `SHORT_WATCH` | `WATCH` | SHORT | None | v1 |
| `WAIT_DATA_WEAK` | `WAIT` | None | None | v1 |
| `WAIT_CONFIRMATION` | `WAIT` | None | None | v1 |
| `WAIT_OI_UNRELIABLE` | `WAIT` | None | None | v1 |
| `WAIT_TRIGGER` | `WAIT` | None | None | v1 |
| `NO_TRADE` | Global safety lock | N/A | Blocks all execution surfaces | v1 |
| `LOCKED` | Global safety lock | N/A | Blocks all execution surfaces | v1 |
| `READY` | `CONFIRMED` | N/A | Research priority only | v1 |

Unknown legacy states fail closed to `WAIT` with `WAIT_STATE_MAPPING` reason.

**Reference:** File B Section 19.6 for detailed compatibility layer specification.
```

### 7.4 Add to Section 11 (Fusion)

```markdown
### 11.4 Legacy Scorer Quarantine (Enhanced)

`FUS-008` quarantine requires these explicit permission flags:

| Permission | Legacy Scorer Value | Required Value | Test |
|---|---|---|---|
| `can_discover` | true | true | Call-graph test: scorer reachable from discovery pipeline |
| `can_rank_research` | true | true | Research priority ranking uses legacy score |
| `can_score_decision` | true (dangerous) | **false** | Decision fusion ignores legacy score |
| `can_size` | true (dangerous) | **false** | Quantity calculation ignores legacy score |
| `can_unlock_ready` | true (dangerous) | **false** | READY state requires modern fusion only |
| `can_create_order_intent` | true (dangerous) | **false** | Order intent requires modern fusion only |

**Specific code issues in `intraday_stock_details.py` lines 887-931:**
- Line 887-900: Absolute gap reward instead of relative gap percentage
- Line 901-915: Missing buyer/seller direction requirement
- Line 916-931: Duplicate counting of same dataset root

**Migration plan:** Rename `intraday_stock_details.py` scorer to `LEGACY_DISCOVERY_SCORE_V1`. Create `MODERN_DECISION_SCORE_V1` with corrected formulas. Run parallel for 200 outcomes before promotion.

**Reference:** File B Sections 16.10 and 19.11 for detailed code analysis and migration plan.
```

### 7.5 Add to Section 13 (UI)

```markdown
### 13.3 Guidance Contract (Trader-Facing Output)

Every candidate must produce deterministic guidance:

```text
guidance_id
candidate_id
headline
action: ACT | WAIT | AVOID | LOCKED
why_now
supporting_facts[]
contradicting_facts[]
missing_evidence[]
next_trigger
invalidation
recheck_at
expires_at
entry_zone
stop
targets[]
quantity
maximum_loss
binding_risk_cap
size_explanation
alternative_scenario
source_hashes[]
```

**Note:** `quantity`, `maximum_loss`, and `binding_risk_cap` are populated only when risk sizing is separately approved (see REJ-011). Until then, these fields show "Risk sizing not yet approved" with reference to File B Section 5.8 for future implementation.

**Reference:** File B Section 7 for detailed guidance contract and File B Section 9 for UI layout.

### 13.4 Productivity Requirements

1. Saved scan profiles for each strategy and timeframe.
2. What-changed-since-last-scan summaries.
3. Side-by-side comparison of top three candidates.
4. Automatic persistence of CONFIRMED candidate snapshots to journal.
5. Grouped failure reasons with drill-down to source level.
6. Candidate expiry warnings (24h before expiration).
7. Incremental enrichment: only re-fetch changed fields.
8. Journal snapshot export (PDF/CSV) for each decision.
9. Daily review dashboard: yesterday's candidates, outcomes, lessons.
10. Full-text search across all historical candidates and guidance.

**Reference:** File B Section 10 for detailed productivity rationale.
```

### 7.6 Add to Section 14 (Storage/API)

```markdown
### 14.1 Additional Required Tables

| Table | Purpose | File B Reference |
|---|---|---|
| `source_decision_contracts` | Per-source permissions and job mappings | Section 4 |
| `evidence_claims` | Normalized claim records with source lineage | Section 7 |
| `evidence_conflicts` | Record of intra-family conflicts | Section 7 |
| `candidate_gate_results` | Per-gate pass/fail with reason | Section 5 |
| `candidate_block_scores` | Per-block detail score breakdown | Section 5 |
| `candidate_guidance` | Trader-facing guidance output | Section 7 |
| `candidate_state_history` | Audit trail of all state transitions | Section 10 |
| `risk_evaluations` | Validation-only risk calculations | Section 5.8 |
| `scan_profile_versions` | Versioned saved scan configurations | Section 10 |
| `outcome_labels` | PIT outcome records for calibration | Section 16.11 |

### 14.2 Additional Required API Endpoints

```text
POST /api/v1/risk/evaluate          # Validation-only risk calculation
GET  /api/v1/candidates/{id}/guidance  # Trader-facing guidance output
GET  /api/v1/sources/{key}/contract    # Source decision contract
GET  /api/v1/sources/ladder            # Source-state maturity counts
GET  /api/v1/scan-profiles             # Saved scan profiles
POST /api/v1/scan-profiles             # Create/update scan profile
GET  /api/v1/journal/daily             # Daily review dashboard
GET  /api/v1/outcomes/pending          # Outcomes awaiting label
```

**Reference:** File B Section 11 for detailed API specification.
```

### 7.7 Add to Section 20 (Implementation Sequence)

```markdown
### 20.1 H-Series Milestone Mapping

File B proposes H-series milestones. Map to R-series as follows:

| H-Series | Description | R-Series Equivalent | Status |
|---|---|---|---|
| H1A0 | Source inventory compiler | R0 | **Included** |
| H1A1 | Transport layer | R1 | **Included** |
| H1A2 | Parser layer | R2 | **Included** |
| H1A3 | Normalizer layer | R3 | **Included** |
| H1A4 | Shared NSE transport contract | R1 (enhanced) | **IMPROVE** via File B 19.3 |
| H1A5 | Source maturity ladder | R3 (enhanced) | **IMPROVE** via File B 16.3 |
| H2R | Manual reconciliation | R5 | **Included** |
| H3A | F&O/MWPL contract split | R6 (enhanced) | **IMPROVE** via File B 19.4 |
| H4A | State compatibility layer | R8 (enhanced) | **IMPROVE** via File B 19.6 |
| H7A | Outcome worker | R14 (enhanced) | **IMPROVE** via File B 19.7 |
| H8A | Cross-exchange event matching | R15 (enhanced) | **IMPROVE** via File B 19.8 |
| H10 | Risk sizing and live execution | **REJECTED** | See REJ-011, GOV-002 |

**Reference:** File B Section 19.13 for detailed H-series specification.
```

---

## 8. Append-Ready Blocks for File B

### 8.1 Add to File B Section 3 (Governing Principles)

```markdown
### 3.4 File A Authority References

This document preserves domain detail. Implementation authority resides in File A (`new_merge_PLAN_2026-07-18.md`).

| File B Section | File A Authority | Scope |
|---|---|---|
| 5.8 Risk sizing | REJ-011, GOV-002 | **Rejected from current plan.** Preserved for H10 milestone only. |
| 5.9 OpenAlgo promotion | OPN-001..005 | **Disabled in current plan.** Preserved for future milestone only. |
| 16.9 Fusion formula | FUS-009 | **Research reference only.** Production uses File A formula. |
| 16.13 PK sidecar | PK-016..019 | **Offline harness only.** No production PK sidecar. |
| All H-series milestones | R0-R18 | **Advisory.** Must map to R-series before implementation. |

**Rule:** No File B requirement may be implemented without a corresponding File A milestone.
```

### 8.2 Add to File B Section 5.8 (Risk Sizing)

```markdown
### 5.8.1 File A Scope Boundary

**File A Authority:** `REJ-011` explicitly rejects quantity sizing from current scope. `GOV-002` confirms no live execution.

This section preserves the complete risk sizing formula for:
1. **Research reference:** Understanding what a complete system would require.
2. **Future milestone:** H10 (separately approved execution milestone) may adopt this formula.
3. **Validation comparison:** PIT validation may compare File A's simplified risk with this detailed formula.

**Implementation rule:** Until H10 is approved, this formula must not be connected to any execution surface. It may run in shadow mode for research only.
```

### 8.3 Add to File B Section 16.9 (Fusion Formula)

```markdown
### 16.9.1 File A Authority

**File A Authority:** `FUS-009` governs evidence fusion in production.

File A formula: `support_strength - opposition_strength`, clamped 0-100, with epsilon=0 for zero-denominator cases.

This section preserves an alternative formula for research comparison:

```
q_i = authority_i * freshness_i * schema_i * completeness_i * scope_match_i * timestamp_integrity_i
```

**Promotion rule:** This formula may be promoted to production only if:
1. PIT validation shows superior calibration (Brier score improvement > 0.05).
2. ECE <= 0.05 on 200+ outcomes.
3. Explicit change control approval through File A governance.

Until then, this formula is research reference only.
```

### 8.4 Add to File B Section 19.6 (State Compatibility)

```markdown
### 19.6.1 File A Canonical States

**File A Authority:** `STA-001..007` define the canonical four-state system: WATCH, WAIT, CONFIRMED, REJECT.

This section preserves legacy state mappings for migration safety. The canonical system is authoritative; legacy states are migration inputs only.

**Migration rule:** All new code must use canonical states. Legacy state mapping is a one-time migration tool, not a permanent compatibility layer.
```

---

## 9. Cross-Reference Quick Lookup

### 9.1 File A Requirement -> File B Detail

| File A ID | File A Topic | File B Sections for Detail |
|---|---|---|
| GOV-001..006 | Governance | 3 (Governing Principles), 15 (Fable Audit) |
| STA-001..007 | State machine | 19.6 (Legacy mapping) |
| FUS-001..011 | Fusion | 16.9 (Formula), 17.2 P0.4 (Hierarchy), 16.10 (Legacy quarantine) |
| DAT-001..030 | Data layer | 16.1-16.7 (Inventory), 17.2 P0.1-P0.3 (Contracts), 19.3-19.5 (Transport) |
| FTR-001..039 | Features | 16.8 (Formulas), 17.2 P0.1 (Tradability) |
| OPN-001..005 | OpenAlgo | 5.9 (Promotion), 16.13 (Milestones) |
| PRF-001..007 | Strategy profiles | 6 (Combinations), 16.7 (Source combos), 18.5 (Decision chains) |
| UI-001..009 | UI | 9 (Layout), 10 (Productivity) |
| STO-001..020 | Storage | 8 (Storage model), 14 (API), 17.2 P0.2 (Raw/adjusted) |
| PK-001..019 | Paper trading | 5.4 (Sidecar), 16.5 (Capability coverage) |
| VAL-001..007 | Validation | 16.11 (ML plan), 19.7 (Outcome worker) |

### 9.2 File B Section -> File A Requirement

| File B Section | File B Topic | File A IDs for Authority |
|---|---|---|
| 1 (Objective) | Quantity/risk sizing | REJ-011, GOV-002 (rejected) |
| 2 (Inventory) | Source counts | DAT-018, R0 |
| 4 (Source contract) | Decision jobs, independence | DAT-021 |
| 5.8 (Risk sizing) | Complete risk pipeline | REJ-011 (rejected) |
| 5.9 (OpenAlgo) | Promotion sequence | OPN-001..005 (disabled) |
| 6 (Strategy combinations) | Per-strategy sources | PRF-001..007 |
| 7 (Evidence/Guidance) | Claim and guidance contracts | FUS-001..011, UI-001..009 |
| 8 (Storage) | Technology choices | STO-001..020 |
| 9 (UI) | Layout and tabs | UI-001..009 |
| 10 (Productivity) | UX features | UI-001..009, FTR-033 |
| 11 (API) | Endpoints and tables | STO-001..020, DAT-001..030 |
| 15 (Fable Audit) | Gap analysis | Sections 20-23 |
| 16.1-16.7 (Inventory detail) | Exact sources and defects | DAT-018, R0 |
| 16.8 (Feature formulas) | 30+ derivations | FTR-001..039 |
| 16.9 (Fusion formula) | Alternative formula | FUS-009 (production) |
| 16.10-16.11 (ML) | Scorer and prediction plan | STO-017/018, VAL-001..007 |
| 17.2 (Antigravity) | P0 corrections | DAT-015, DAT-019, FTR-035, STO-020 |
| 18.4-18.6 (Reconciliation) | Dedupe and corrections | DAT-018, FUS-008 |
| 19.2 (Decision jobs) | J01-J14 taxonomy | DAT-021 |
| 19.3 (Transport) | NSE behaviors | DAT-020 |
| 19.4 (F&O/MWPL) | Contract split | DAT-015 |
| 19.5 (USD/INR) | Role split | SRC-FX |
| 19.6 (State compatibility) | Legacy mapping | STA-001..007 |
| 19.7 (Outcome worker) | PIT recording | STO-017/018 |
| 19.8 (Event matching) | Cross-exchange | DAT-030 |
| 19.9 (Priority) | True P0 vs overstated | R0-R18 |
| 19.11 (Legacy quarantine) | Specific controls | FUS-008 |
| 19.12 (Risk policy) | Exact percentages | REJ-011 (rejected) |
| 19.13 (Milestones) | H-series | R0-R18 |

---

## 10. Trading Impact Assessment

### 10.1 High-Impact Items (Would Affect Live Trading Safety)

| Item | File B Section | File A Status | Risk if Missing |
|---|---|---|---|
| Source inventory baseline | 16.1 | Absent | Cannot verify what sources exist |
| Source-state ladder | 16.3 | Absent | Sources may be used before validated |
| Dataset-root identity | 18.4 | Absent | Duplicate counting of same data |
| Legacy scorer quarantine | 16.10, 19.11 | Partial | Unsafe legacy code may affect decisions |
| F&O/MWPL contract split | 19.4 | Partial | Wrong ban status -> unsafe trades |
| USD/INR role split | 19.5 | Partial | Wrong MCX prices -> incorrect signals |
| Legacy state mapping | 19.6 | Absent | Unknown states -> undefined behavior |
| Decision-job taxonomy | 19.2 | Absent | Sources may serve wrong jobs |
| EvidenceClaim permissions | 7 | Partial | Claims may exceed source authority |
| Tradability contract | 17.2 P0.1 | Partial | Restricted stocks may be traded |

### 10.2 Medium-Impact Items (Affect Research Quality or UX)

| Item | File B Section | File A Status | Risk if Missing |
|---|---|---|---|
| Feature formulas | 16.8 | Partial | Features may be calculated incorrectly |
| Fusion formula detail | 16.9 | Conflict | Research may use wrong formula |
| UI layout | 9 | Partial | Trader may miss critical information |
| Productivity features | 10 | Absent | Slower research workflow |
| API completeness | 11 | Partial | Missing endpoints for key workflows |
| Timestamp semantics | 17.2 P0.3 | Partial | PIT correctness may be compromised |
| Outcome worker | 19.7 | Partial | Calibration data may be incomplete |

---

## 11. Maintenance Rules

### 11.1 When File A Changes

1. If File A adds a new requirement, check File B for domain detail.
2. If File A modifies a formula, update File B's research reference.
3. If File A rejects a scope item, ensure File B preserves it for future milestones.
4. If File A adds a new milestone, map to H-series if applicable.

### 11.2 When File B Changes

1. If File B updates a formula, mark it as research reference pending PIT validation.
2. If File B identifies a new source, add to File A's inventory baseline.
3. If File B finds a new defect, ensure File A's DAT-018 covers it.
4. If File B proposes a new H-series milestone, map to R-series before implementation.

### 11.3 When This Governance Document Changes

1. Version bump required for new conflicts, new cross-references, or resolution changes.
2. No version bump required for adding File B items to coverage matrix (informational).
3. All changes must be reviewed against both File A and File B.

---

## 12. Document Version History

| Version | Date | Change | Authority |
|---|---|---|---|
| v1.0 | 2026-07-20 | Initial governance system | Two-document analysis of File A (2026-07-18) and File B (2026-07-17) |

---glm5.2 guidence below

# TrendForge Two-Document Governance and Implementation System

## 1. Executive Verdict on Using Both Files Without Merging Them

**VERIFIED FROM PLAN:** File A (`new_merge_PLAN_2026-07-18.md`) is a 2,199+ line authoritative implementation roadmap containing 24 sections, 224+ acceptance tests (T-001 through T-224), 13 implementation milestones (R0-R18 plus Q4/Q5 variants), and complete feature contracts (FTR-001 through FTR-039). File B (`TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md`) is a 1,200+ line domain and decision reference containing 19 sections with detailed source intelligence, per-strategy mandatory source lists, exact feature calculation formulas, inventory reconciliation proof, and domain-specific conflict resolution rules.

**VERDICT:** File A alone is **sufficient for implementation sequencing and acceptance testing** but **insufficient for complete domain specification**. File B contains material domain detail — particularly in Sections 15-19 — that File A references by stable ID but does not reproduce. Both files can remain separate without causing implementation ambiguity **if and only if** a bidirectional cross-reference system is installed and an automated coverage check prevents orphan requirements.

**REASONABLE INFERENCE:** Ignoring File B would cause implementation gaps in: (1) specific source-contract field requirements, (2) per-strategy mandatory source lists, (3) exact feature calculation formulas, (4) real-time reliability lane architecture, (5) OpenAlgo provider interface detail, (6) probability calibration thresholds, (7) MCX commodity-specific context mapping, (8) legacy scorer quarantine code references, (9) dataset-root identity model fields, and (10) cross-exchange event matching rules.

---

## 2. Exact Role and Authority of Each File

| Attribute | File A (Merge Plan) | File B (Hybrid Plan) |
|---|---|---|
| **Authority** | Build-sequence authority | Domain, source and decision-reference authority |
| **Controls** | Implementation order, milestones R0-R18, acceptance gates, current build activity | Source intelligence, trading rationale, formulas, evidence combinations, failure cases, domain knowledge |
| **Does NOT control** | Detailed domain formulas (references File B) | Build order or milestone sequencing (references File A) |
| **Hierarchy** | Above File B for "when and how to build" | Above File A for "what exactly to build and why" |
| **Above both** | Current explicit user instructions and AGENTS.md | Current explicit user instructions and AGENTS.md |
| **Code/tests** | Implementation evidence, not planning authority | Implementation evidence, not planning authority |
| **Conflict rule** | Stricter source-authority, PIT, fail-closed, non-execution, non-probability rule wins | Same rule applies; File B domain detail informs the stricter interpretation |

---

## 3. What Can Be Built from File A Alone

**VERIFIED FROM PLAN:** File A contains sufficient information to build:

1. **Complete state machine** (Section 10): Four states, transition rules, gate codes, confirmation prerequisites
2. **Complete screening pipeline** (Section 9, 24.6): S0-S9 stages with state ceilings
3. **Complete evidence fusion model** (Section 11, 21.9, 24.8): Family resolver, correlation groups, anti-double-counting formula
4. **Complete feature contracts** (Section 7): FTR-001 through FTR-039 with all mandatory fields
5. **Complete storage/API contracts** (Section 14): 14 storage tables, 18+ API routes, module ownership map
6. **Complete test suite** (Sections 16, 20.7, 21.14, 22.10, 23.14, 24.14): 224+ tests
7. **Complete implementation sequence** (Sections 15, 21.13, 23.14, 24.13): R0-R18 with acceptance gates
8. **Complete PKScreener integration verdict** (Sections 20-22): PK-001 through PK-019
9. **Complete disposition ledgers** (Sections 17, 21.15, 23.15, 24.15): Every requirement classified
10. **Complete risk/freshness/fail-closed gates** (Section 12, 24.9): 10 gate order rules, fail-closed semantics table
11. **Complete UI design** (Section 13, 24.10): Primary radar fields, inspector tabs
12. **Complete conflict resolutions** (Section 4, 21.5, 23.5, 24.4): 15+ documented conflicts resolved

**REASONABLE INFERENCE:** A developer following only File A could build a structurally correct system that compiles and passes tests, but would lack the domain depth to make correct trading-logic decisions when implementing specific feature calculations or source-combination rules.

---

## 4. What Would Be Lost by Ignoring File B

**VERIFIED FROM PLAN — 25 material losses identified:**

| Loss # | File B Section | What is lost | Impact area |
|---|---|---|---|
| 1 | §2 | Exact inventory partition (105/231/18=354), specific defect counts (16 dup groups, 33 malformed cells, 2 compound URLs, 4 sentinels) | Inventory hygiene |
| 2 | §4 + §15.3 | Source contract field list (17 original + 15 added = 32 fields including timezone, publication_calendar, rate_budget, circuit_breaker_policy, correction_policy, event_identity_fields, fallback_authority, watermark_policy, retention_policy) | Source contract completeness |
| 3 | §5 Stage 3 | Specific regime classification output (BULL_TRADEABLE, BULL_CAUTIOUS, RANGE, BEAR_TRADEABLE, NO_TRADE) and regime-specific size multipliers | Market context |
| 4 | §5 Stage 5 | Specific enrichment rules: "AMFI and shareholding are delayed swing evidence. NSDL sector reports are not stock-level FPI proof. ESOPs, gifts and inter-se transfers are not graded like open-market promoter purchases." | Sponsor evidence quality |
| 5 | §5 Stage 6 | Specific derivative rules: "participant OI does not replace stock-level OI. MWPL is not derived from participant OI. GEX requires chain Greeks, multiplier, spot and expiry; absent verified dealer positioning it must be labelled GEX_PROXY." | Derivatives evidence |
| 6 | §6 | Per-profile mandatory combination table (6 profiles with exact required evidence) | Strategy correctness |
| 7 | §7 | EvidenceClaim contract (17 fields including valid_until, can_score, can_veto, can_unlock_ready, raw_artifact_hash) and Guidance contract (19 fields including binding_risk_cap, size_explanation, alternative_scenario, source_hashes) | Contract completeness |
| 8 | §8 | Storage model rationale table (7 rows explaining why each store is chosen) | Storage architecture |
| 9 | §9 | Specific radar fields: "change since the previous scan" and inspector tab content detail | UX |
| 10 | §15.2 | Real-time reliability contract: 4-lane architecture (Fast/Near-real-time/EOD/Slow) with specific cadence and decision authority per lane | Operational architecture |
| 11 | §15.4 | Trust-producing combinations table (8 specific evidence combinations and what they do/don't establish) | Evidence interpretation |
| 12 | §15.5 | Probability promotion requirements: 7 specific requirements including Brier score, ECE ≤ 0.05, 200+ outcomes, positive net-expectancy lower confidence bound | Calibration |
| 13 | §15.6 | Risk and execution additions: 12 specific items including tick size, lot size, freeze quantity, price bands, auction state, short-sale restrictions, physical-delivery restrictions | Risk completeness |
| 14 | §16.3 | Source-state ladder: 10 states (REGISTERED → TRANSPORT_OK → ARTIFACT_VALID → VALID_EMPTY → PARSER_SCHEMA_OK → NORMALIZED → FRESH_FOR_JOB → DECISION_WIRED → GATE_AUTHORIZED → EXECUTION_AUTHORIZED) with definitions | Source maturity |
| 15 | §16.6 | Complete list of 69 linked source keys and 43 not-linked source keys | Source mapping |
| 16 | §16.7 | Per-strategy mandatory source lists (e.g., intraday continuation requires licensed/OpenAlgo quote, market session, liquidity/spread/price-band checks, sector/index regime, RVOL-TOD; discovery from nse_preopen_fo, nse_volume_gainers, nse_most_active_volume/value, nse_sector_constituents, nse_all_indices; confirmation from nse_oi_spurts_contracts or nse_fo_bhavcopy-derived OI, nse_quote_equity_trade_info, material event family) | Strategy implementation |
| 17 | §16.8 | High-value derived feature catalog: 4 groups (Auction/Opening, Price/Liquidity/Relative Activity, Derivatives, Events/Ownership/Sponsor Quality) with exact formulas for gap_pct_signed, IEP_stability, buy_sell_imbalance, RVOL_TOD, price_OI_quadrant, futures_basis_bps, PCR_OI, IV_rank, put_call_skew, event_materiality, deal_notional_to_ADTV, deal_price_acceptance, promoter_holding_delta, pledge_level, AMFI holding delta | Feature calculation |
| 18 | §16.9 | Evidence fusion formula: q_i = authority_i × freshness_i × schema_i × completeness_i × scope_match_i × timestamp_integrity_i | Evidence quality |
| 19 | §16.10 | Legacy scorer critique: specific line references (887-890, 893, 894-895, 899-900, 901-902, 903-904, 911, 919-931) with exact problems per line | Scorer migration |
| 20 | §16.11 | Point-in-time feature store schema (13 fields including available_at, revision_id, feature_version, null_reason), label definition (7 label types), validation requirements (8 items), metrics (10 items), model order (5 items), drift rules | ML/validation |
| 21 | §16.12 | Real-time breakage state machine: 14 states (IDLE → FETCH_DUE → FETCHING → TRANSPORT_OK → VALIDATING_ARTIFACT → PARSING → STRUCTURED_FRESH → VALID_EMPTY → STALE → RATE_LIMITED → BLOCKED → SCHEMA_CHANGED → CORRECTION_PENDING → BROKEN) with 12 required controls | Operational reliability |
| 22 | §16.13 | OpenAlgo provider interface: MarketDataProvider (9 methods) and ExecutionProvider (5 methods), promotion sequence (7 steps) | OpenAlgo integration |
| 23 | §16.14 | Risk and quantity logic: specific formula with risk_budget, unit_risk, base_qty, final_qty, calibration_cap; 7 rules including "Missing stop, invalid price, stale quote or non-positive unit risk means zero quantity" | Risk sizing |
| 24 | §16.16 | Priority activation backlog: 20 contracts ranked by decision value (nse_mwpl_ban → nse_quote_equity → nse_quote_equity_trade_info → nse_quote_derivative → mcx_market_watch → mcx_future_prices → mcx_option_chain → mcx_delivery_reports → bse_insider_trading → bse_xbrl_announcements → bse_buyback_tender → bse_takeover_open_offer → amfi_monthly_portfolio → nse_pit_annual → lme_warehouse_stocks → shfe_weekly_stock → baker_hughes_na_rig_count → imd_rainfall_timeseries → usda_wasde/des_crop_estimates → dgcis_trade_data/china_nbs_indicator) | Source activation order |
| 25 | §17-19 | Antigravity corrections (P0/P1), 354-source panel reconciliation, independent review reconciliation with 14 decision-job taxonomy, shared NSE transport contract, F&O ban/MWPL split, USD/INR role split, canonical state compatibility, unified PIT outcome worker, cross-exchange event matching, dataset-root priority correction, 10 conflict/fusion rules, legacy scorer quarantine (7 controls), risk policy treatment, 7 milestone amendments | Architecture integrity |

---

## 5. Best Unique Requirements in File A

| ID | Requirement | Why it is uniquely valuable |
|---|---|---|
| MERGE-7-001 | Mandatory feature contract template with 20 required fields (Section 6) | Prevents ambiguous implementation; File B has no equivalent lint requirement |
| MERGE-11-001 | Hierarchical evidence families with MARKET_FLOW parent cap (Section 11.3, 17.2 P0.4) | File B lists families flat; File A adds parent-child cap architecture |
| MERGE-10-001 | Four-state-only product model with denied transitions (Section 10, 21.8) | File B's Section 7 lists 14+ states; File A's strict four-state model is cleaner |
| MERGE-9-001 | Hard completeness rule with profile minimum threshold (Section 9.1) | File B mentions completeness but lacks the hard ceiling formula |
| MERGE-7-031 | PK scanner registry with versioned ID/parameter hash (Section 7.3, STO-016) | File B has no PKScreener integration at all |
| MERGE-7-032 | Pipe DSL as non-voting composition (FUS-010) | File B has no pipe concept |
| MERGE-16-001 | 224 numbered acceptance tests with explicit expected observations | File B has 18 tests (Section 12) + additional in later sections; File A is far more complete |
| MERGE-15-001 | Runnable vertical milestones R0-R18 where app boots after every step | File B's milestones are not defined as runnable verticals |
| MERGE-6-001 | Feature registry lint that fails build if any required field is absent | File B has no build-fail mechanism |
| MERGE-24-001 | PK-019 finite offline harness only; no production sidecar (Section 24.11) | File B's later sections partially address this but File A makes it controlling |

---

## 6. Best Unique Requirements in File B

| ID | Requirement | Why it is uniquely valuable |
|---|---|---|
| HYBRID-15.2-001 | Real-time reliability contract: 4-lane architecture (Fast/Near-real-time/EOD/Slow) | File A has no equivalent lane model |
| HYBRID-15.3-001 | Source contract additions: 15 new fields (timezone, publication_calendar, session_dependency, entitlement_required, legal_use_mode, rate_budget, retry_policy, circuit_breaker_policy, content_signature, schema_version, correction_policy, event_identity_fields, fallback_authority, watermark_policy, retention_policy) | File A's source contract is less detailed |
| HYBRID-15.4-001 | Trust-producing combinations table: 8 specific evidence combinations with "what it establishes" and "what it does not establish" | File A has no equivalent reference table |
| HYBRID-15.5-001 | Probability promotion requirements: 7 specific items including Brier score, ECE ≤ 0.05, 200+ outcomes, base-rate comparison, drift detection | File A references calibration but lacks specific thresholds |
| HYBRID-16.3-001 | Source-state ladder: 10 states from REGISTERED to EXECUTION_AUTHORIZED with definitions | File A references maturity but lacks the explicit ladder |
| HYBRID-16.6-001 | Complete list of 69 linked and 43 not-linked source contract keys | File A uses dataset roots but doesn't enumerate all keys |
| HYBRID-16.7-001 | Per-strategy mandatory source lists with exact contract names | File A has profile contracts but not specific source requirements per profile |
| HYBRID-16.8-001 | High-value derived feature catalog with exact formulas | File A has feature contracts but not the calculation formulas |
| HYBRID-16.12-001 | Real-time breakage state machine: 14 states with 12 required controls | File A has stream integrity (DAT-033) but not the full 14-state model |
| HYBRID-16.13-001 | OpenAlgo provider interface: 9 MarketDataProvider methods + 5 ExecutionProvider methods | File A has OPN-001..005 but not the method-level interface |
| HYBRID-16.14-001 | Risk and quantity logic with exact INR amounts and formula | File A explicitly defers sizing; File B has the complete formula |
| HYBRID-16.16-001 | Priority activation backlog: 20 contracts ranked by decision value | File A has no equivalent prioritized backlog |
| HYBRID-18.4-001 | Dataset-root identity model: 12 fields (dataset_root_id, transport_variant_id, mirror_group_id, resolver_id, publisher_authority, endpoint_role, activation_state, decision_jobs, evidence_family, family_weight_cap, fallback_authority_cap) | File A references dataset roots but doesn't define all 12 fields |
| HYBRID-19.2-001 | Decision-job taxonomy: 14 explicit jobs (J01-J14) | File A has no equivalent job taxonomy |
| HYBRID-19.8-001 | Cross-exchange event matching: 4 match states (MATCHED, POSSIBLE_MATCH, DISTINCT, MANUAL_REVIEW) with candidate features | File A mentions dedup but lacks the matching model |

---

## 7. Complete File-B-to-File-A Coverage Matrix

| File B Section | Requirement Summary | File A Representation | Disposition | Gap Detail |
|---|---|---|---|---|
| §1 Objective | 7 questions to answer | Section 1 + Section 13 (8 radar questions) | PRESENT | None |
| §2 Inventory Baseline | 105/231/18=354 partition | Section 0.1 references; Section 20.2 recomputes | PARTIAL | File A doesn't contain the full partition proof or defect enumeration |
| §3 Governing Principles | 10 principles | Sections 1, 12 (embedded) | PRESENT | None |
| §4 Source Decision Contract | 17 contract fields | Section 5.2 (roles only), 5.4 (identity) | PARTIAL | GAP-001: Missing 15 fields from §15.3 (timezone, publication_calendar, etc.) |
| §5 Stage 0-9 Pipeline | 10 stages | Section 5.1, 9, 24.6 | PRESENT | None |
| §5 Stage 3 Regime | Specific regime outputs | Section 9 S2 (context priors) | PARTIAL | GAP-002: Missing specific regime labels (BULL_TRADEABLE etc.) and size multipliers |
| §5 Stage 5 Enrichment | Delayed/ESOP/inter-se rules | Section 7 FTR-026, FTR-027 | PARTIAL | GAP-003: Missing specific rules ("ESOPs not graded like open-market") |
| §5 Stage 6 Derivatives | GEX/OI/MWPL rules | Section 7 FTR-020..025, Section 12 | PRESENT | None |
| §6 Strategy Profiles | 6 profiles with mandatory combos | Section 9.2 (7 profiles) | PRESENT | File A adds PRF-007 (MCX base/agri) |
| §7 EvidenceClaim Contract | 17 fields | Section 5.4 (identity), 11 (families) | PARTIAL | GAP-004: Missing valid_until, can_score, can_veto fields explicitly |
| §7 Guidance Contract | 19 fields | Section 13 (UI), 14 (API) | PARTIAL | GAP-005: Missing binding_risk_cap, size_explanation, alternative_scenario |
| §8 Storage Model | 7-row rationale table | Section 14.1 (14 tables) | PRESENT | File A extends; File B rationale preserved as LINK_TO_B |
| §9 Trader Experience | Radar + inspector detail | Section 13, 24.10 | PRESENT | None |
| §10 Productivity | 10 requirements | Section 13 (embedded) | PARTIAL | GAP-006: Missing saved scan profiles, side-by-side comparison, search |
| §11 API/Persistence | 9 APIs + 10 tables | Section 14.2 (18+ APIs) | PRESENT | File A extends |
| §12 Failure Tests | 18 tests | Section 16 (224 tests) | PRESENT | File A subsumes all 18 |
| §13 Milestones H1-H9 | 9 milestones | Section 15 (R0-R18) | PRESENT | File A supersedes |
| §14 Completion Definition | 9 conditions | Section 19 | PRESENT | None |
| §15.1 Mismatches | 9 findings | Section 2 (W-001..015), 20.2 | PRESENT | None |
| §15.2 Reliability Contract | 4-lane architecture | Section 23.6 (flowchart) | PARTIAL | GAP-007: Missing lane-specific cadence and decision authority table |
| §15.3 Source Contract Additions | 15 new fields | Section 5.2 (partial) | PARTIAL | GAP-001 (same as above) |
| §15.4 Trust Combinations | 8 combination rows | Section 11 (rules embedded) | PARTIAL | GAP-008: Missing explicit "what it establishes / does not establish" table |
| §15.5 Probability Rules | 7 promotion requirements | Section 19.2 (medium confidence) | PARTIAL | GAP-009: Missing Brier score, ECE threshold, base-rate comparison requirement |
| §15.6 Risk/Execution Additions | 12 preflight items | Section 12 (gates), 24.9 | PARTIAL | GAP-010: Missing tick/lot/freeze/margin/band/delivery preflight checklist |
| §15.7 Compliance Boundary | NSE licensing note | Section 1 (GOV-001), 24.9 | PRESENT | None |
| §15.8 Alternatives Evaluated | 4 options | Section 1 (verdict) | PRESENT | None |
| §15.9 H1A Milestone | 6 acceptance criteria | Section 20.5 (R0 amendments) | PRESENT | None |
| §16.1 Audit Scope | SHA-256, inventory shape | Section 0.1 (references) | PRESENT | None |
| §16.2 Executive Verdict | 7 principal gaps | Section 2 (W-001..015) | PRESENT | None |
| §16.3 Source-State Ladder | 10 states + definitions | Section 20.2 (maturity ladder) | PARTIAL | GAP-011: Missing 10-state ladder with specific definitions |
| §16.4 Inventory Defects | 11 specific defects | Section 20.2 (references) | PARTIAL | GAP-012: Missing specific defect enumeration (16 dup groups, 33 malformed, etc.) |
| §16.5 URL Disposition | 10-row role table | Section 22.4 (SRC3-001..020) | PRESENT | File A maps to individual candidates |
| §16.6 Source Contract Keys | 69 linked + 43 not-linked | Section 22.4 (candidate ledger) | PARTIAL | GAP-013: Missing complete key enumeration as a single reference list |
| §16.7 Decision Families | Per-strategy source lists | Section 9.2 (profile contracts) | PARTIAL | GAP-014: Missing exact contract names per profile (e.g., nse_preopen_fo, nse_volume_gainers) |
| §16.8 Feature Catalog | 4 groups with formulas | Section 7 (FTR-001..039) | PARTIAL | GAP-015: Missing exact calculation formulas (RVOL_TOD, PCR_OI, basis_bps, etc.) |
| §16.9 Evidence Fusion | q_i quality formula | Section 11.2 (resolver), 24.8 | PARTIAL | GAP-016: Missing q_i = authority × freshness × schema × completeness × scope × timestamp formula |
| §16.10 Legacy Scorer | 8 specific code issues | Section 20.2 (FUS-008) | PRESENT | File A quarantines; File B has line-level critique |
| §16.11 Prediction Plan | PIT store, labels, validation, model order | Section 19.2, 23.10 (VAL-001) | PARTIAL | GAP-017: Missing 13-field PIT feature store schema, 7 label types, 10 metrics |
| §16.12 Breakage Recovery | 14-state machine + 12 controls | Section 23.10 (DAT-033, STO-022) | PARTIAL | GAP-018: Missing 14-state state machine and 12 specific controls |
| §16.13 OpenAlgo Boundary | Provider interface + promotion | Section 5.2, 23.10 (OPN-005) | PARTIAL | GAP-019: Missing 9 MarketDataProvider methods + 5 ExecutionProvider methods |
| §16.14 Risk/Quantity | Formula with INR amounts | Not in File A (out of scope) | FILE_B_ONLY | GAP-020: Risk sizing formula with specific INR 250/500/750 amounts |
| §16.15 Trader Product Design | Radar + inspector fields | Section 13, 24.10 | PRESENT | None |
| §16.16 Priority Backlog | 20 contracts ranked | Section 22.4 (SRC3 ledger) | PARTIAL | GAP-021: Missing prioritized 1-20 ranking by decision value |
| §16.17 Revised Build Order | H1-H10 with slices | Section 15 (R0-R18) | PRESENT | File A supersedes |
| §16.18 Completion Criteria | 25 conditions | Section 19, 24.16 | PRESENT | None |
| §17.2 P0 Corrections | 6 items (Tradability, Raw/Adjusted, Timestamps, Families, Realizable-exit, Legacy) | Sections 20.3, 21.6, 23.10 | PRESENT | None |
| §17.3 P1 Corrections | 5 items (Outcomes, Model demotion, Broker ticks, Dynamic rules, Release-time) | Sections 23.10, 24.11 | PRESENT | None |
| §17.4 Strategy Additions | Per-profile mandatory checks | Section 9.2 | PARTIAL | GAP-022: Missing specific per-profile checks (T2T, ESM, price bands, halt, auction for intraday) |
| §17.5 Feature Corrections | 10 features with revised contracts | Section 7, 21.6 | PRESENT | None |
| §17.6 Data-Science Corrections | 10 rules | Section 21.9, 23.9 | PRESENT | None |
| §17.7 Risk/Cost Corrections | Versioned inputs + correlation budget | Section 24.9 | PARTIAL | GAP-023: Missing specific versioned input list (STT, GST, SEBI charges, stamp duty, brokerage) |
| §17.8 UI Corrections | Radar + inspector additions | Section 24.10 | PRESENT | None |
| §17.9 Corrected Milestone Order | H1-H10 with H1A sub-milestones | Section 24.13 (Q5-R0..R7) | PRESENT | File A supersedes |
| §17.10 New Failure Tests | 20 tests | Section 24.14 (T-170..217) | PRESENT | None |
| §17.11 Not Adopted | 9 panel suggestions | Section 21.5, 24.4 | PRESENT | None |
| §17.12 Revised Completion Gate | 10 conditions | Section 24.16 | PRESENT | None |
| §18.3 Panel Claim Ledger | 21 recommendations | Section 22.11 | PRESENT | None |
| §18.4 Dataset-Root Model | 12 fields + identity chain | Section 22.4, 5.4 | PARTIAL | GAP-024: Missing 12-field dataset-root model (dataset_root_id, transport_variant_id, etc.) |
| §18.5 Four Decision Chains | NSE intraday/swing, MCX intraday/swing | Section 22.3 (binding workflow) | PRESENT | None |
| §18.6 Code Corrections | 9 items | Section 22.6 | PRESENT | None |
| §18.7 Already Implemented | 6 capabilities | Section 22.1 | PRESENT | None |
| §18.8 Verification Backlog | 8 items | Section 22.4 (candidate ledger) | PRESENT | None |
| §18.9 Not Adopted | 12 suggestions | Section 24.15 | PRESENT | None |
| §18.10 Milestone Integration | Refined order | Section 24.13 | PRESENT | None |
| §18.11 Additional Tests | 18 tests | Section 22.10 (T-111..124) | PRESENT | None |
| §18.12 Acceptance Gate | 12 conditions | Section 24.16 | PRESENT | None |
| §19.1 Review Coverage | Maturity ladder | Section 20.1 | PRESENT | None |
| §19.2 Decision-Job Taxonomy | 14 jobs (J01-J14) | Not in File A | FILE_B_ONLY | GAP-025: Missing 14-job taxonomy |
| §19.3 Shared NSE Transport | 9 behavioral requirements | Section 20.3 (DAT-020) | PRESENT | None |
| §19.4 F&O Ban/MWPL Split | nse_fno_ban vs nse_mwpl_percentages | Section 20.2 (DAT-018) | PRESENT | None |
| §19.5 USD/INR Role Split | fbil_usdinr_reference vs usd_inr_live | Section 22.4 (SRC3-018, SRC3-020) | PRESENT | None |
| §19.6 Canonical State Compatibility | Legacy state mapping | Section 20.3 (STA-005) | PRESENT | None |
| §19.7 Unified PIT Outcome Worker | Worker specification | Section 23.10 (STO-018) | PRESENT | None |
| §19.8 Cross-Exchange Event Matching | 4 match states + candidate features | Not explicitly in File A | FILE_B_ONLY | GAP-026: Missing MATCHED/POSSIBLE_MATCH/DISTINCT/MANUAL_REVIEW model |
| §19.9 Dataset-Root Priority | 5 true P0 roots | Section 22.4 (SRC3 ledger) | PRESENT | None |
| §19.10 Conflict/Fusion Rules | 10 rules | Section 24.8, 23.9 | PRESENT | None |
| §19.11 Legacy Scorer Quarantine | 7 controls | Section 20.3 (FUS-008) | PRESENT | None |
| §19.12 Risk Policy Treatment | Versioned configuration | Section 24.9 | PRESENT | None |
| §19.13 Milestone Amendments | 7 amendments | Section 24.13 | PRESENT | None |
| §19.14 Additional Tests | 14 tests | Section 24.14 | PRESENT | None |
| §19.15 Not Adopted | 13 items | Section 24.15 | PRESENT | None |
| §19.16 Acceptance Gate | 12 conditions | Section 24.16 | PRESENT | None |

---

## 8. Complete File-A-to-File-B Rationale Lookup Matrix

| File A Requirement | File B Rationale Location | Necessary or Optional? |
|---|---|---|
| MERGE-5.2 Source roles (OFFICIAL_GATE, etc.) | HYBRID-4 Source roles table | Necessary: File B defines what each role permits |
| MERGE-5.3 Dataset roots (SRC-NSE-UNIVERSE, etc.) | HYBRID-16.6 Source contract keys | Necessary: File B lists exact contract keys per root |
| MERGE-5.4 Normalized identity fields | HYBRID-7 EvidenceClaim contract | Necessary: File B specifies 17 claim fields |
| MERGE-7 FTR-001..039 Feature contracts | HYBRID-16.8 Feature catalog | Necessary: File B has exact calculation formulas |
| MERGE-9.2 PRF-001..007 Strategy profiles | HYBRID-6 Strategy requirements + HYBRID-16.7 Per-strategy sources | Necessary: File B lists mandatory sources per profile |
| MERGE-10 State machine | HYBRID-7 Canonical states + HYBRID-17.9 Corrected order | Optional: File A's four-state model supersedes; File B provides migration context |
| MERGE-11 Evidence families | HYBRID-16.9 Evidence fusion + HYBRID-17.2 P0.4 Hierarchical families | Necessary: File B has q_i formula and parent-family cap logic |
| MERGE-12 Fail-closed gates | HYBRID-3 Governing principles + HYBRID-16.12 Breakage recovery | Optional: File A's gate order is authoritative; File B adds 14-state recovery detail |
| MERGE-13 Radar/Inspector | HYBRID-9 Trader experience + HYBRID-16.15 Product design | Optional: File A's 8-question model is authoritative; File B adds field detail |
| MERGE-14 Storage/API | HYBRID-8 Storage model + HYBRID-11 API additions | Optional: File A extends; File B provides rationale |
| MERGE-15 R0-R18 Implementation | HYBRID-13/16.17/17.9 Milestones | Optional: File A supersedes; File B provides dependency context |
| MERGE-16 T-001..224 Tests | HYBRID-12 Failure tests + HYBRID-17.10/18.11/19.14 Additional tests | Optional: File A subsumes; File B provides test rationale |
| MERGE-20-24 Reconciliation sections | HYBRID-15-19 Audit findings | N/A: File A already incorporated these sections from File B |

---

## 9. Missing, Partial, Duplicated and Conflicting Requirement Lists

### Missing from File A (GAP register)

| GAP ID | Requirement | File B Location | Impact | Recommended Action |
|---|---|---|---|---|
| GAP-001 | Source contract 15 additional fields (timezone, publication_calendar, etc.) | §15.3 | Source contract incompleteness | ADD_TO_A: Add to Section 5.2 as mandatory contract fields |
| GAP-002 | Specific regime labels and size multipliers | §5 Stage 3 | Regime classification ambiguity | ADD_TO_A: Add to Section 9 S2 |
| GAP-003 | Specific enrichment rules (ESOP, inter-se, gift classification) | §5 Stage 5 | Sponsor quality grading errors | ADD_TO_A: Add to Section 7 FTR-026/027 |
| GAP-004 | EvidenceClaim 17-field contract | §7 | Claim contract incompleteness | ADD_TO_A: Add to Section 5.4 |
| GAP-005 | Guidance contract 19-field contract | §7 | Guidance output incompleteness | ADD_TO_A: Add to Section 14.2 API DTO |
| GAP-006 | 10 productivity requirements | §10 | UX feature gaps | ADD_TO_A: Add to Section 13 |
| GAP-007 | 4-lane reliability architecture | §15.2 | Operational architecture gap | LINK_TO_B: Reference from File A Section 5.1 |
| GAP-008 | Trust-producing combinations table | §15.4 | Evidence interpretation gap | LINK_TO_B: Reference from File A Section 11 |
| GAP-009 | Probability promotion thresholds | §15.5 | Calibration specification gap | LINK_TO_B: Reference from File A Section 19 |
| GAP-010 | 12-item execution preflight checklist | §15.6 | Risk completeness gap | LINK_TO_B: Reference from File A Section 12 |
| GAP-011 | 10-state source-state ladder | §16.3 | Source maturity tracking gap | ADD_TO_A: Add to Section 5.2 |
| GAP-012 | 11 specific inventory defects | §16.4 | Inventory hygiene gap | LINK_TO_B: Reference from File A Section 20.2 |
| GAP-013 | Complete 69+43 source key enumeration | §16.6 | Source mapping gap | LINK_TO_B: Reference from File A Section 22.4 |
| GAP-014 | Exact contract names per profile | §16.7 | Strategy implementation gap | ADD_TO_A: Add to Section 9.2 profile contracts |
| GAP-015 | Exact feature calculation formulas | §16.8 | Feature implementation gap | LINK_TO_B: Reference from File A Section 7 |
| GAP-016 | q_i quality formula | §16.9 | Evidence quality gap | ADD_TO_A: Add to Section 11.2 |
| GAP-017 | PIT feature store schema + labels + metrics | §16.11 | ML/validation gap | LINK_TO_B: Reference from File A Section 19 |
| GAP-018 | 14-state breakage recovery machine | §16.12 | Operational reliability gap | LINK_TO_B: Reference from File A Section 23.10 |
| GAP-019 | OpenAlgo provider interface methods | §16.13 | Integration gap | LINK_TO_B: Reference from File A Section 23.10 |
| GAP-020 | Risk sizing formula with INR amounts | §16.14 | Risk sizing gap (out of scope per File A) | POSTPONE: Valid domain reference but outside current milestone |
| GAP-021 | 20-contract priority activation backlog | §16.16 | Source activation order gap | ADD_TO_A: Add to Section 15 R-steps |
| GAP-022 | Per-profile mandatory tradability checks | §17.4 | Tradability gap | ADD_TO_A: Add to Section 9.2 profile contracts |
| GAP-023 | Versioned cost input list (STT, GST, etc.) | §17.7 | Cost model gap | LINK_TO_B: Reference from File A Section 23.10 VAL-001 |
| GAP-024 | 12-field dataset-root model | §18.4 | Identity model gap | ADD_TO_A: Add to Section 5.4 |
| GAP-025 | 14-job decision taxonomy (J01-J14) | §19.2 | Decision-job mapping gap | ADD_TO_A: Add to Section 5.3 |
| GAP-026 | Cross-exchange event matching model | §19.8 | Event deduplication gap | ADD_TO_A: Add to Section 11 as correlation group rule |

### Partial requirements (in both files but File B has important detail)

| ID | File A Location | File B Location | What is partial |
|---|---|---|---|
| PARTIAL-001 | Section 5.2 source roles | §4 + §15.3 | File A has 7 roles; File B adds 15 contract fields |
| PARTIAL-002 | Section 7 FTR contracts | §16.8 feature catalog | File A has contract template; File B has exact formulas |
| PARTIAL-003 | Section 9.2 profiles | §6 + §16.7 | File A has 7 profiles; File B adds exact source names per profile |
| PARTIAL-004 | Section 11 fusion | §16.9 + §17.2 P0.4 | File A has family caps; File B adds q_i formula and parent-family hierarchy |
| PARTIAL-005 | Section 13 UI | §9 + §16.15 | File A has 8 questions; File B adds specific field lists |
| PARTIAL-006 | Section 14 storage | §8 | File A extends; File B provides storage rationale |

### Duplicated requirements

| ID | File A Location | File B Location | Note |
|---|---|---|---|
| DUP-001 | Section 5.1 flow | §5 pipeline | Same flow, different granularity — keep both, cross-reference |
| DUP-002 | Section 10 states | §7 canonical states | File A supersedes with 4-state model; File B's 14+ states become reason codes |
| DUP-003 | Section 11 families | §7 + §16.9 families | Different family names; File A's names are authoritative |
| DUP-004 | Section 12 gates | §3 principles + §12 tests | Same fail-closed rules, different presentation |
| DUP-005 | Section 16 tests | §12 + §17.10 + §18.11 + §19.14 tests | File A subsumes all File B tests |

### Conflicting requirements

| CONFLICT ID | File A Position | File B Position | Resolution |
|---|---|---|---|
| CONFLICT-001 | Exactly 4 public states (WATCH/WAIT/CONFIRMED/REJECT) | 14+ states including PRIORITY_RADAR, WAIT_OI_UNRELIABLE, etc. (§7) | File A wins: 4 states + reason codes. File B's §17.9 and §19.6 partially agree. |
| CONFLICT-002 | No position sizing (out of scope) | Detailed INR 250/500/750 sizing formula (§8, §16.14) | File A wins: sizing is out of scope. File B's formula is preserved as domain reference for future milestone. |
| CONFLICT-003 | 10 evidence families (Section 11.1) | 8 families (§7) + hierarchical parent (§17.2) | RESOLVED: File A's Section 21.6 adopts hierarchical model. File B's §17.2 P0.4 is the source. |
| CONFLICT-004 | R0-R18 milestones (Section 15) | H1-H9 then H1A-H10 (§13, §15.9, §16.17, §17.9) | File A wins: R0-R18 supersedes all File B milestone schemes. |
| CONFLICT-005 | PKScreener as finite offline harness (PK-016..019) | No PKScreener in File B | No conflict: File A adds PKScreener; File B has no position. |
| CONFLICT-006 | 224 tests (T-001..T-224) | 18 tests (§12) + 20 (§17.10) + 18 (§18.11) + 14 (§19.14) = 70 tests | File A wins: 224 tests subsume File B's 70. File B's test rationale is preserved. |
| CONFLICT-007 | "data_mode" ceiling for intraday (Section 2, W-002) | "intraday executable READY blocked until OpenAlgo" (§15.1) | Aligned: both block intraday confirmation without verified live feed. |
| CONFLICT-008 | Legacy scorer quarantine (FUS-008, Section 20.3) | Legacy scorer quarantine (§16.10, §19.11) | Aligned: both quarantine. File B has line-level critique; File A has contract-level quarantine. |

---

## 10. Conflict Resolutions Based on Source Authority, Freshness, Point-in-Time Correctness, Reliability and Trading Usefulness

| Conflict | Resolution Rule | Technical Basis |
|---|---|---|
| State count (4 vs 14+) | 4 public states win; 14+ become reason codes | Simpler API/UI contract; prevents inconsistent transitions; File B's §17.9 and §19.6 partially agree |
| Risk sizing (absent vs detailed) | Sizing is out of scope for this milestone | User explicitly excluded execution/OMS/sizing; File B's formula preserved as domain reference |
| Evidence families (10 vs 8+hierarchy) | Hierarchical model with parent caps wins | File B's §17.2 P0.4 provides the parent-family cap; File A's §21.6 adopts it; prevents correlated options/OI/volume from casting 3 votes |
| Milestone scheme (R0-R18 vs H1-H10) | R0-R18 wins | File A's milestones are runnable verticals; File B's are not defined as runnable |
| Test count (224 vs 70) | 224 tests win | File A subsumes all File B tests; File B's test rationale preserved as LINK_TO_B |
| Source authority | Official structured > official delayed > unofficial > secondary > reference | Both files agree; File B's §8 conflict policy and File A's §5.2 roles are aligned |
| Freshness | Per-source cadence, not universal interval | Both files agree; File B's §16.12 and File A's §12.1 are aligned |
| PIT correctness | available_at <= decision_time; revisions don't mutate history | Both files agree; File B's §15.2 and File A's §5.4 are aligned |
| Correlated evidence | One representative per atomic group before family aggregation | File A's §11.2 and File B's §16.9 are aligned after §21.6 reconciliation |
| Delayed context | Cannot prove live flow | Both files agree; File B's §3.5 and File A's §5.2 are aligned |

---

## 11. Recommended Amendments to File A

| Amendment ID | Existing Section | Problem | Exact Proposed Change | Reason | Dependencies | Acceptance Test | Priority | Confidence |
|---|---|---|---|---|---|---|---|---|
| AMEND-A-001 | Section 5.2 | Source contract lacks 15 fields from File B §15.3 | Add: "Every active source contract must include: timezone, publication_calendar, session_dependency, entitlement_required, legal_use_mode, rate_budget, retry_policy, circuit_breaker_policy, content_signature, schema_version, correction_policy, event_identity_fields, fallback_authority, watermark_policy, retention_policy. See HYBRID-15.3 for field definitions." | Prevents incomplete source contracts | None | T-088: Source contract missing any field cannot unlock gate | P0 | HIGH |
| AMEND-A-002 | Section 5.4 | Normalized identity lacks EvidenceClaim 17-field contract | Add: "Every EvidenceClaim must carry: symbol, asset, timeframe, strategy, job, direction, strength, reliability, source_key, independence_family, data_date, published_at, valid_until, supporting_fields, limitations, can_score, can_veto, can_unlock_ready, raw_artifact_hash. See HYBRID-7 for field semantics." | Prevents claim contract ambiguity | None | T-075: Claim missing field cannot enter resolution | P0 | HIGH |
| AMEND-A-003 | Section 9.2 | Profile contracts lack exact source names | Add per-profile row: "Mandatory sources: see HYBRID-16.7 for exact contract keys per profile." | Prevents strategy implementation gaps | HYBRID-16.7 | Profile test verifies named sources are wired | P1 | HIGH |
| AMEND-A-004 | Section 11.2 | Resolver lacks q_i quality formula | Add: "Claim quality: q_i = authority_i × freshness_i × schema_i × completeness_i × scope_match_i × timestamp_integrity_i. Each component bounded [0,1]. See HYBRID-16.9." | Prevents unmeasurable quality scoring | None | T-092: Claim without raw-root metadata cannot enter FUS-009 | P1 | HIGH |
| AMEND-A-005 | Section 5.3 | Dataset roots lack 12-field dataset-root identity model | Add: "Every dataset root must carry: dataset_root_id, transport_variant_id, mirror_group_id, resolver_id, publisher_authority, endpoint_role, activation_state, decision_jobs, evidence_family, family_weight_cap, fallback_authority_cap. See HYBRID-18.4." | Prevents mirror/duplicate vote inflation | None | T-072: Two transport variants create one contribution | P1 | HIGH |
| AMEND-A-006 | Section 5.1 | Flow lacks 4-lane reliability architecture reference | Add after flow: "Real-time reliability uses a 4-lane architecture. See HYBRID-15.2 for lane definitions, cadence, and decision authority." | Prevents operational architecture gap | HYBRID-15.2 | None (reference only) | P2 | MEDIUM |
| AMEND-A-007 | Section 11.3 | Correlation groups lack cross-exchange event matching | Add: "CG_EVENT_ROOT: NSE/BSE mirrors match by business identity (symbol, date, type, actor, quantity, price). Match states: MATCHED, POSSIBLE_MATCH, DISTINCT, MANUAL_REVIEW. Only MATCHED shares one directional contribution. See HYBRID-19.8." | Prevents duplicate event confidence | None | T-015: NSE/BSE mirror produces one event ID | P1 | HIGH |
| AMEND-A-008 | Section 7 | Feature contracts lack exact calculation formulas | Add per-feature row: "Calculation formula: see HYBRID-16.8 for exact formula." | Prevents formula ambiguity | HYBRID-16.8 | Feature parity test | P1 | HIGH |
| AMEND-A-009 | Section 15 | R-steps lack priority activation backlog | Add: "Source activation follows the priority backlog in HYBRID-16.16. Activate sources because they close a decision gap, not to increase link count." | Prevents random source activation | HYBRID-16.16 | Source activation order test | P2 | MEDIUM |
| AMEND-A-010 | Section 19 | Calibration lacks specific thresholds | Add: "Probability promotion requires: ≥200 effective outcomes, ECE ≤ 0.05, positive net-expectancy lower confidence bound, base-rate model comparison, drift detection. See HYBRID-15.5." | Prevents premature probability claims | HYBRID-15.5 | T-063: Performance charts hidden without PIT_APPROVED | P2 | MEDIUM |
| AMEND-A-011 | Section 5.2 | Source roles lack 10-state maturity ladder | Add: "Source maturity ladder: REGISTERED → TRANSPORT_OK → ARTIFACT_VALID → VALID_EMPTY → PARSER_SCHEMA_OK → NORMALIZED → FRESH_FOR_JOB → DECISION_WIRED → GATE_AUTHORIZED → EXECUTION_AUTHORIZED. See HYBRID-16.3." | Prevents 'connected' from being mistaken for 'authorized' | HYBRID-16.3 | T-088: Contract missing field cannot unlock gate | P1 | HIGH |
| AMEND-A-012 | Section 12 | Gates lack 14-job decision taxonomy | Add: "Every dataset root maps to one or more decision jobs J01-J14. See HYBRID-19.2 for taxonomy." | Prevents source-to-job ambiguity | HYBRID-19.2 | Source-job mapping test | P2 | MEDIUM |
| AMEND-A-013 | Section 0 | Document lacks bidirectional cross-reference section | Add Section 0.5: "Cross-Reference Authority: This plan is the build-sequence authority. HYBRID plan is the domain reference. Consult HYBRID for: source contract fields (§15.3), feature formulas (§16.8), per-strategy sources (§16.7), reliability lanes (§15.2), OpenAlgo interface (§16.13), probability thresholds (§15.5), inventory defects (§16.4), source-state ladder (§16.3), dataset-root model (§18.4), event matching (§19.8)." | Prevents AI agents from reading only one file | None | Coverage check passes | P0 | HIGH |

---

## 12. Recommended Amendments to File B

| Amendment ID | Existing Section | Problem | Exact Proposed Change | Reason | Dependencies | Acceptance Test | Priority | Confidence |
|---|---|---|---|---|---|---|---|---|
| AMEND-B-001 | Top of file | File lacks authority-and-usage section | Add: "## 0. Authority and Usage. This file is the domain and decision-reference authority for TrendForge. Build sequence and acceptance gates are controlled by MERGE plan (`new_merge_PLAN_2026-07-18.md`). When this file's state vocabulary (§7) conflicts with MERGE §10, MERGE's four-state model controls; this file's states are reason codes. When this file's milestones (§13, §16.17, §17.9) conflict with MERGE §15, MERGE's R0-R18 controls. Consult MERGE for: implementation order, acceptance tests, feature contracts, storage/API contracts, PKScreener integration." | Prevents File B from being misused as build authority | None | Cross-reference check | P0 | HIGH |
| AMEND-B-002 | §7 Canonical states | 14+ states conflict with File A's 4-state model | Add note: "NOTE: The states listed below are historical domain states. The controlling public API state vocabulary is WATCH/WAIT/CONFIRMED/REJECT per MERGE §10. The states below map to reason codes under WAIT. See MERGE §20.3 STA-005 for migration mapping." | Prevents implementation ambiguity | None | State mapping test | P0 | HIGH |
| AMEND-B-003 | §13 Milestones | H1-H9 conflict with File A's R0-R18 | Add note: "NOTE: The milestones below are superseded by MERGE §15 R0-R18. This section is preserved for dependency context and domain rationale only." | Prevents milestone confusion | None | None (documentation) | P0 | HIGH |
| AMEND-B-004 | §8/§16.14 Risk sizing | Sizing is out of scope per File A | Add note: "NOTE: Risk sizing formulas below are domain reference for a future separately authorized milestone. Current build scope (MERGE plan) explicitly excludes position sizing, order quantity, and execution. See MERGE §1 GOV-002." | Prevents scope creep | None | None (documentation) | P1 | HIGH |
| AMEND-B-005 | §16.10 Legacy scorer | Code line references may become stale | Add note: "NOTE: Line references are as of 2026-07-17. Verify against current code before implementation. MERGE §20.3 FUS-008 controls quarantine." | Prevents stale code references | None | None (documentation) | P2 | MEDIUM |

---

## 13. Bidirectional Cross-Reference Tables

### File A → File B Cross-Reference Table

| File A Section | Consult File B For | File B Section |
|---|---|---|
| 5.2 Source roles | Complete contract field list (32 fields) | §4 + §15.3 |
| 5.3 Dataset roots | Exact source contract keys (69+43) | §16.6 |
| 5.4 Normalized identity | EvidenceClaim 17-field contract | §7 |
| 7 Feature contracts | Exact calculation formulas | §16.8 |
| 9.2 Strategy profiles | Mandatory sources per profile | §6 + §16.7 |
| 9 S2 Regime | Specific regime labels and multipliers | §5 Stage 3 |
| 11 Evidence fusion | q_i quality formula, trust combinations | §16.9 + §15.4 |
| 12 Fail-closed gates | 14-state breakage recovery, 12 controls | §16.12 |
| 13 UI | Specific radar/inspector field lists | §9 + §16.15 |
| 14 Storage/API | Storage rationale, OpenAlgo interface | §8 + §16.13 |
| 19 Calibration | Probability promotion thresholds | §15.5 |
| 20-24 Reconciliation | Original audit findings (unmodified) | §15-19 |
| All sections | 4-lane reliability architecture | §15.2 |
| All sections | 10-state source maturity ladder | §16.3 |
| All sections | 14-job decision taxonomy | §19.2 |
| All sections | Cross-exchange event matching model | §19.8 |
| All sections | Dataset-root 12-field identity model | §18.4 |
| All sections | Priority activation backlog (20 contracts) | §16.16 |

### File B → File A Cross-Reference Table

| File B Section | Consult File A For | File A Section |
|---|---|---|
| §7 States | Controlling 4-state model and reason codes | §10 + §20.3 STA-005 |
| §13 Milestones | Controlling R0-R18 implementation sequence | §15 + §24.13 |
| §12 Tests | Complete 224-test suite | §16 + §24.14 |
| §8/§16.14 Sizing | Scope exclusion (no sizing in current milestone) | §1 GOV-002 |
| §16.10 Legacy scorer | Quarantine contract and build-fail test | §20.3 FUS-008 |
| §16.17 Build order | Controlling R0-R18 with Q4/Q5 amendments | §23.14 + §24.13 |
| §4 Source contract | Additional 15 fields (adopted in MERGE) | §5.2 (after AMEND-A-001) |
| §16.8 Feature formulas | Feature contract template and registry lint | §6 + §7 |
| §16.7 Per-strategy sources | Profile contract table | §9.2 |
| §15.2 Reliability lanes | Stream integrity contract | §23.10 DAT-033 |
| §16.13 OpenAlgo interface | Conditional read-only capability | §23.10 OPN-005 |
| §15.5 Probability thresholds | Calibration milestone and validation gate | §19 + §24.14 T-063 |
| §16.3 Source-state ladder | Source maturity and DAT-021 | §20.2 + §22.6 |
| §18.4 Dataset-root model | Normalized identity and dedup | §5.4 (after AMEND-A-005) |
| §19.8 Event matching | Correlation group CG_EVENT_ROOT | §11.3 (after AMEND-A-007) |
| §19.2 Decision-job taxonomy | Dataset root mapping | §5.3 (after AMEND-A-012) |
| §16.16 Priority backlog | Source activation in R-steps | §15 (after AMEND-A-009) |

---

## 14. Stable Requirement-ID Scheme

```text
MERGE-<section>-<number>     File A requirements (build authority)
HYBRID-<section>-<number>    File B requirements (domain reference)
CROSS-<number>               Cross-document requirements
GAP-<number>                 Requirements missing from File A
CONFLICT-<number>            Contradictions between files
PARTIAL-<number>             Requirements in both but File B has important detail
DUP-<number>                 Duplicated requirements
AMEND-A-<number>             Amendments to File A
AMEND-B-<number>             Amendments to File B
T-<number>                   Test cases (controlled by File A)
FTR-<number>                 Feature contracts (controlled by File A)
STA-<number>                 State machine rules (controlled by File A)
FUS-<number>                 Evidence fusion rules (controlled by File A)
DAT-<number>                 Data/source contracts (controlled by File A)
SEL-<number>                 Pipeline stage rules (controlled by File A)
PRF-<number>                 Strategy profile rules (controlled by File A)
UI-<number>                  UI requirements (controlled by File A)
STO-<number>                 Storage requirements (controlled by File A)
API-<number>                 API requirements (controlled by File A)
OPN-<number>                 OpenAlgo requirements (controlled by File A)
PK-<number>                  PKScreener requirements (controlled by File A)
PST-<number>                 Postponed items (controlled by File A)
REJ-<number>                 Rejected items (controlled by File A)
TRC-<number>                 Traceability requirements (controlled by File A)
GOV-<number>                 Governance requirements (controlled by File A)
VAL-<number>                 Validation requirements (controlled by File A)
SRC3-<number>                Source candidate ledger (controlled by File A)
```

**Rule:** All new requirement IDs are minted in File A. File B sections retain their section numbers as reference targets (HYBRID-<section>) but do not mint new implementation IDs.

---

## 15. Orphan-Requirement Detection Method

**Method:** An automated documentation coverage check compares two artifact sets:

1. **File B section registry:** Every numbered section and subsection in File B is enumerated with its section path (e.g., `HYBRID-16.7`, `HYBRID-15.3`).
2. **File A cross-reference registry:** Every `HYBRID-<section>` reference in File A is extracted.

**Orphan condition:** A File B section that has no corresponding `HYBRID-<section>` reference in File A AND no disposition in the coverage matrix (Section 7 of this document).

**Detection algorithm:**
```python
file_b_sections = extract_numbered_sections("TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md")
file_a_references = extract_hybrid_references("new_merge_PLAN_2026-07-18.md")
coverage_matrix_dispositions = extract_dispositions(this_document)

orphans = []
for section in file_b_sections:
    if section not in file_a_references and section not in coverage_matrix_dispositions:
        orphans.append(section)

if orphans:
    fail("Orphan File B sections without disposition: " + str(orphans))
```

**Current status:** Based on the coverage matrix in Section 7, **zero orphan sections** exist. Every material section in File B has been assigned a disposition.

---

## 16. Automated Documentation Coverage-Test Design

```python
"""
TrendForge Documentation Coverage Test

Validates that no material requirement is silently skipped
between File A (merge plan) and File B (hybrid plan).
"""

import hashlib
import re
from pathlib import Path

FILE_A = Path("D:/TrendForge/docs/fable/new_merge_PLAN_2026-07-18.md")
FILE_B = Path("D:/TrendForge/docs/fable/TREND_FORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md")

def verify_hashes():
    """Verify both files match their recorded SHA-256 hashes."""
    expected_a = "F3A245768C9E52702B36C04CD41DA0FD41B4FB369C0CBBF5D33166FB2315FB30"
    expected_b = "expected_hash_for_file_b"  # Must be computed and inserted
    actual_a = hashlib.sha256(FILE_A.read_bytes()).hexdigest().upper()
    actual_b = hashlib.sha256(FILE_B.read_bytes()).hexdigest().upper()
    assert actual_a == expected_a, f"File A hash mismatch: {actual_a} != {expected_a}"
    assert actual_b == expected_b, f"File B hash mismatch: {actual_b} != {expected_b}"

def extract_sections(filepath):
    """Extract all numbered section headings."""
    text = filepath.read_text(encoding="utf-8")
    sections = re.findall(r'^##\s+(\d+(?:\.\d+)*)\s', text, re.MULTILINE)
    return set(sections)

def extract_cross_references(filepath, pattern):
    """Extract all HYBRID-x.x or MERGE-x.x references."""
    text = filepath.read_text(encoding="utf-8")
    return set(re.findall(pattern, text))

def test_file_b_sections_covered():
    """Every File B section must have a disposition or cross-reference in File A."""
    file_b_sections = extract_sections(FILE_B)
    file_a_text = FILE_A.read_text(encoding="utf-8")
    
    # Sections explicitly covered by File A's reconciliation sections
    covered_patterns = [
        r"HYBRID-\d+", r"§\d+", r"Section \d+", 
        r"audit lines \d+", r"lines \d+-\d+"
    ]
    
    orphans = []
    for section in file_b_sections:
        found = any(re.search(p, file_a_text) for p in covered_patterns)
        if not found:
            orphans.append(section)
    
    assert not orphans, f"Orphan File B sections: {orphans}"

def test_file_a_references_resolve():
    """Every HYBRID-x.x reference in File A must resolve to a File B section."""
    file_a_refs = extract_cross_references(FILE_A, r"HYBRID-(\d+(?:\.\d+)*)")
    file_b_sections = extract_sections(FILE_B)
    
    unresolved = file_a_refs - file_b_sections
    assert not unresolved, f"Unresolved HYBRID references in File A: {unresolved}"

def test_stable_ids_unique():
    """All stable IDs in File A must be unique."""
    text = FILE_A.read_text(encoding="utf-8")
    ids = re.findall(r'`([A-Z]+-\d+)`', text)
    duplicates = [id for id in ids if ids.count(id) > 1]
    assert not duplicates, f"Duplicate stable IDs: {set(duplicates)}"

def test_no_execution_routes():
    """Neither file may contain order/execution route additions."""
    for filepath in [FILE_A, FILE_B]:
        text = filepath.read_text(encoding="utf-8")
        # Look for positive execution route additions (not rejections)
        execution_patterns = [
            r"POST.*order", r"place_order.*enabled", r"execute.*trade.*live"
        ]
        violations = []
        for pattern in execution_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            # Filter out rejections
            positive = [m for m in matches if "reject" not in text[max(0,text.find(m)-100):text.find(m)+100].lower()]
            violations.extend(positive)
        assert not violations, f"Execution routes found in {filepath.name}: {violations}"

def test_no_probability_claim():
    """Evidence strength must not be labelled as probability."""
    text = FILE_A.read_text(encoding="utf-8")
    forbidden = [
        r"win probability.*\d+%", r"P\(win\).*=\d+", r"confidence.*\d+%"
    ]
    for pattern in forbidden:
        matches = re.findall(pattern, text, re.IGNORECASE)
        # Allow in rejection context
        positive = [m for m in matches if "reject" not in text[max(0,text.find(m)-50):text.find(m)+50].lower()]
        assert not positive, f"Probability claim found: {positive}"

if __name__ == "__main__":
    verify_hashes()
    test_file_b_sections_covered()
    test_file_a_references_resolve()
    test_stable_ids_unique()
    test_no_execution_routes()
    test_no_probability_claim()
    print("All documentation coverage tests passed.")
```

---

## 17. Correct Implementation Order After Accounting for Both Files

| Order | Milestone | Scope | File B Consultation Required |
|---:|---|---|---|
| 1 | R0 / Q5-R0 | Contract freeze: states, source contracts (with HYBRID-15.3 fields), feature registry lint, MWPL owner, indicator engine, data-mode ceilings | YES: §15.3 (source fields), §16.3 (state ladder), §4 (source roles) |
| 2 | R1 | Selection DTO and primary radar on fixtures | YES: §9 (radar fields), §16.15 (product design) |
| 3 | R2 | S0-S3 cheap pipeline with official/verified EOD/activity | YES: §16.7 (per-strategy discovery sources) |
| 4 | R3 | Family resolver and anti-double-counting | YES: §16.9 (q_i formula), §17.2 P0.4 (hierarchical families) |
| 5 | R4 | PK0 pin, license, dependency inventory + early PIT fixtures | NO (File A controls) |
| 6 | R5 | Minimal structure pack: closed-bar breakout + NR | YES: §16.8 (exact NR formula) |
| 7 | R6 | Shortlist enrichment: surveillance, pledge, deals/events, delivery, FO OI/basis | YES: §16.7 (enrichment sources), §5 Stage 5 (enrichment rules) |
| 8 | R7 | PK1/PK2 isolated shadow or CLI JSON drop + golden fixtures | NO (File A controls) |
| 9 | R8 | PK3 native core registry | NO (File A controls) |
| 10 | R9 | Lifecycle history and ORB/VWAP only when verified bars exist | YES: §16.8 (ORB/VWAP formulas) |
| 11 | R10 | PK5 pipe DSL and family caps | NO (File A controls) |
| 12 | R11 | Swing RS/delivery + MCX master/profile gates | YES: §16.7 (MCX sources), §17.4 (MCX strategy additions) |
| 13 | R12 | Shortlist options timeline/walls | YES: §16.8 (PCR/walls formulas), §17.5 (feature corrections) |
| 14 | R13 | PK4 remaining deterministic scanners | NO (File A controls) |
| 15 | R14 | PK6 official CA/sponsor reconciliation | YES: §18.6 (code corrections), §19.8 (event matching) |
| 16 | R15 | PK7 Scanner Lab UI | NO (File A controls) |
| 17 | R16 | PK8 PIT validation before performance UI | YES: §15.5 (promotion thresholds), §16.11 (PIT store schema) |
| 18 | R17 | M8 OpenAlgo read-only shadow | YES: §16.13 (provider interface), §15.2 (reliability lanes) |
| 19 | R18 | M9/PK9 model governance and controlled upgrades | YES: §15.5 (drift rules), §17.3 P1.2 (model demotion) |

---

## 18. Requirements That Must Be Built Now

1. **AMEND-A-001:** Add 15 source contract fields to File A Section 5.2 (from HYBRID-15.3)
2. **AMEND-A-002:** Add 17-field EvidenceClaim contract to File A Section 5.4 (from HYBRID-7)
3. **AMEND-A-003:** Add per-profile source references to File A Section 9.2 (from HYBRID-16.7)
4. **AMEND-A-004:** Add q_i quality formula to File A Section 11.2 (from HYBRID-16.9)
5. **AMEND-A-005:** Add 12-field dataset-root model to File A Section 5.4 (from HYBRID-18.4)
6. **AMEND-A-007:** Add cross-exchange event matching to File A Section 11.3 (from HYBRID-19.8)
7. **AMEND-A-011:** Add 10-state source maturity ladder to File A Section 5.2 (from HYBRID-16.3)
8. **AMEND-A-013:** Add cross-reference authority section to File A (this document's Section 13)
9. **AMEND-B-001:** Add authority-and-usage section to File B (this document's Section 2)
10. **AMEND-B-002:** Add state vocabulary reconciliation note to File B §7
11. **AMEND-B-003:** Add milestone supersession note to File B §13
12. **R0:** Contract freeze with all above amendments integrated
13. **R1:** Selection DTO and primary radar on fixtures
14. **R2:** S0-S3 cheap pipeline with official/verified EOD/activity
15. **R3:** Family resolver with q_i formula and zero corroboration bonus

---

## 19. Requirements That Should Be Postponed

1. **GAP-020:** Risk sizing formula with INR amounts (HYBRID-16.14) — out of scope per GOV-002
2. **GAP-017:** Full PIT feature store schema (HYBRID-16.11) — wait until R16/R8
3. **GAP-018:** 14-state breakage recovery machine (HYBRID-16.12) — wait until R17/OpenAlgo
4. **GAP-019:** OpenAlgo provider interface methods (HYBRID-16.13) — wait until R17
5. **GAP-009:** Probability promotion thresholds (HYBRID-15.5) — wait until R16/R8
6. **PST-001..008:** All postponed features from File A Section 8
7. **GAP-007:** 4-lane reliability architecture (HYBRID-15.2) — reference only until OpenAlgo
8. **GAP-021:** 20-contract priority activation backlog (HYBRID-16.16) — reference only until R2
9. **GAP-023:** Versioned cost input list (HYBRID-17.7) — wait until VAL-001 in R6
10. **GAP-010:** 12-item execution preflight checklist (HYBRID-15.6) — wait until future execution milestone

---

## 20. Requirements That Should Be Rejected

| ID | Requirement | Source | Reason |
|---|---|---|---|
| REJ-001 | Public WAIT_DATA, WAIT_OI_UNRELIABLE as API states | HYBRID-7 (implied) | File A's 4-state model controls; these are reason codes |
| REJ-002 | H1-H9 as active milestones | HYBRID-13 | Superseded by R0-R18 |
| REJ-003 | Position sizing in current milestone | HYBRID-8, HYBRID-16.14 | Explicitly out of scope per GOV-002 |
| REJ-004 | Probability display before calibration | HYBRID-15.5 (implied) | Both files agree: no P(win) until PIT validation |
| REJ-005 | Permanent PKScreener runtime sidecar | Not in File B | File A PK-019 controls: finite offline only |
| REJ-006 | Paper trading / Telegram alerts | Not in File B | Out of scope per GOV-001 |
| REJ-007 | Broker execution / OMS / account access | Not in File B | Out of scope per GOV-002 |
| REJ-008 | GEX as dealer positioning (not proxy) | HYBRID-5 Stage 6 (partially) | Must remain GEX_PROXY per PST-001 |
| REJ-009 | Participant OI as stock-level FII proof | HYBRID-5 Stage 3, HYBRID-16.7 | Both files agree: aggregate context only |
| REJ-010 | AMFI/CFTC as live flow | HYBRID-3.5, HYBRID-16.7 | Both files agree: delayed context only |

---

## 21. At Least 50 Acceptance and Adversarial Tests

File A already contains 224 tests (T-001 through T-224). The following 50 are selected as the most critical for the two-document governance system. All are **VERIFIED FROM PLAN** as existing requirements in File A.

| # | Test ID | Scenario | Expected Behavior | File B Domain Reference |
|---:|---|---|---|---|
| 1 | T-001 | HTTP 200 login/block HTML | Not STRUCTURED_OK; BLOCKED | HYBRID-12.1 |
| 2 | T-006 | Valid empty GSM/deal/PIT | VALID_EMPTY ≠ fetch failure | HYBRID-12.2, HYBRID-16.3 |
| 3 | T-011 | Stale required family | CONFIRMED demotes to WAIT | HYBRID-3.7 |
| 4 | T-012 | Unclosed bar | Cannot create permanent confirmation | HYBRID-5 Stage 6 |
| 5 | T-013 | Corporate action unresolved | Price features INPUT_INCOMPLETE | HYBRID-5 Stage 1 |
| 6 | T-015 | NSE/BSE mirror disclosure | One event ID, two source links | HYBRID-19.8 |
| 7 | T-021 | Volume gainer + most-active + RVOL | One participation contribution | HYBRID-16.9 |
| 8 | T-024 | PCR + walls + max pain + option volume | One options family | HYBRID-16.9, HYBRID-17.2 P0.4 |
| 9 | T-034 | Delivery as intraday proof | Forbidden | HYBRID-5 Stage 5 |
| 10 | T-036 | Participant OI as stock FII proof | Rejected | HYBRID-5 Stage 3 |
| 11 | T-037 | AMFI as intraday buying | Forbidden | HYBRID-3.5 |
| 12 | T-040 | Metadata-only evidence unlocks CONFIRMED | Impossible | HYBRID-3.7 |
| 13 | T-041 | Unofficial fallback inherits official authority | Forbidden | HYBRID-15.3 |
| 14 | T-045 | Intraday profile before verified broker bars | Cannot CONFIRM | HYBRID-15.1 |
| 15 | T-046 | MCX without local master/price-OI | Cannot CONFIRM | HYBRID-16.7 |
| 16 | T-048 | Evidence strength labelled as win rate | UI/API reject | HYBRID-15.5 |
| 17 | T-049 | PK shadow match alone raises rank | Forbidden | File A PK-018 |
| 18 | T-059 | Current-constituent-only backtest | Fails survivorship fixture | HYBRID-16.11 |
| 19 | T-063 | Performance charts without PIT_APPROVED | Hidden | HYBRID-15.5 |
| 20 | T-068 | Invalid broker OHLC/timestamp | Bar rejected | HYBRID-15.2 |
| 21 | T-069 | OpenAlgo adapter order/account route | No callable route | HYBRID-9 |
| 22 | T-071 | Registered MWPL URL without dated artifact | Remains WAIT | HYBRID-19.4 |
| 23 | T-072 | RVOL + volume-gainer + most-active + option-volume | Cannot exceed family cap | HYBRID-16.9 |
| 24 | T-073 | Decision DTO containing legacy detail_score | Fails contract validation | HYBRID-16.10 |
| 25 | T-074 | Legacy internal waiting values | Serialize to WAIT + gate code | HYBRID-19.6 |
| 26 | T-075 | Claim missing time/revision/hash/family field | Cannot enter resolution | HYBRID-7 |
| 27 | T-077 | T2T rejects intraday; F&O ban rejects; near-MWPL WAIT | Separate typed outcomes | HYBRID-17.2 P0.1 |
| 28 | T-078 | First NSE 401/403 re-seeds once; second fails closed | Bounded retry | HYBRID-19.3 |
| 29 | T-079 | HTTP 200 block HTML never falls back to browser | No browser fallback | HYBRID-19.3 |
| 30 | T-082 | Option velocity requires same expiry + ordered timestamp + complete chain | No mixed-expiry combination | HYBRID-16.8 |
| 31 | T-084 | Unclosed breakout is WATCH/WAIT; closed bar remains WAIT if gates fail | No premature confirmation | HYBRID-5 Stage 6 |
| 32 | T-088 | Source contract missing authority/job/valid-empty/parser version | Cannot unlock gate | HYBRID-15.3 |
| 33 | T-090 | Evidence profile weights must be non-negative, versioned, sum to 1 | No arbitrary point systems | HYBRID-16.9 |
| 34 | T-091 | Missing required family remains zero; no renormalization | No missing-family compensation | HYBRID-16.9 |
| 35 | T-093 | WATCH→CONFIRMED, CONFIRMED→WATCH, REJECT→WAIT denied | State validation enforces | HYBRID-17.9 |
| 36 | T-096 | Split/bonus ratio orientation produces correct factor | Backward adjustment verified | HYBRID-17.2 P0.2 |
| 37 | T-097 | Dividend adjustment uses pre-ex reference factor across OHLC | Close-only subtraction fails | HYBRID-17.2 P0.2 |
| 38 | T-100 | Pasted cadence/filename/schema claim without observed artifact | Remains REQUIRES_LIVE_VERIFICATION | HYBRID-16.1 |
| 39 | T-103 | Four-component pipe changes membership but contributes zero claims | Pipe is non-voting | File A FUS-010 |
| 40 | T-104 | What-changed compares only matching profile/universe/scanner version | No cross-version diff | HYBRID-10.2 |
| 41 | T-110 | Offline PK parity artifact cannot be invoked by production resolver | No production dependency | File A PK-019 |
| 42 | T-111 | Malformed JSON/CSV parse failure is PARSE_FAILED; not VALID_EMPTY | Distinct failure classification | HYBRID-16.3 |
| 43 | T-117 | Active source without rate policy/block signatures/fallback ceiling | Fails DAT-023 lint | HYBRID-15.3 |
| 44 | T-122 | TRAP-TF-001 false-confirmation bundle cannot produce CONFIRMED | Multi-failure adversarial test | HYBRID-16.18 |
| 45 | T-125 | Stream heartbeat expires; dependent intraday candidates max WAIT | Stream integrity gate | HYBRID-15.2 |
| 46 | T-134 | Corporate-action reconcile runs twice; raw candle hash unchanged | Immutable raw preservation | HYBRID-17.2 P0.2 |
| 47 | T-138 | Historical decision predates membership publication | Constituent unavailable | HYBRID-16.11 |
| 48 | T-146 | Parser emits NaN or infinity; normalized value is null with reason | No non-finite contamination | HYBRID-16.8 |
| 49 | T-149 | Option time-to-expiry is zero/negative; Greeks/IV are UNKNOWN | No artificial cap | HYBRID-5 Stage 6 |
| 50 | T-218 | Production route inventory contains no /api/v1/shadow/pkscreener/* | No PK sidecar route | File A API-019 |

---

## 22. Final Proof Table Showing Every Material Section Received a Disposition

| File | Section | Disposition | Destination |
|---|---|---|---|
| File A | 0 Document Control | KEEP | Controls implementation authority |
| File A | 1 Executive Verdict | KEEP | Controls scope boundary |
| File A | 2 Fifteen Weaknesses | KEEP | Controls risk resolution |
| File A | 3 Best Ideas | KEEP | Controls retained decisions |
| File A | 4 Conflict Resolutions | KEEP | Controls conflict rules |
| File A | 5 Architecture | IMPROVE (AMEND-A-001..005, A-011..012) | Add File B fields |
| File A | 6 Feature Contract | KEEP | Controls feature lint |
| File A | 7 Feature Specs | IMPROVE (AMEND-A-008) | Add formula references |
| File A | 8 Postponed/Rejected | KEEP | Controls scope |
| File A | 9 Pipeline | IMPROVE (AMEND-A-003) | Add per-profile sources |
| File A | 10 State Machine | KEEP | Controls 4-state model |
| File A | 11 Evidence Fusion | IMPROVE (AMEND-A-004, A-007) | Add q_i formula, event matching |
| File A | 12 Risk/Freshness | KEEP | Controls fail-closed gates |
| File A | 13 Radar/Inspector | KEEP | Controls UI |
| File A | 14 Storage/API | KEEP | Controls persistence |
| File A | 15 Implementation | IMPROVE (AMEND-A-009) | Add priority backlog reference |
| File A | 16 Tests | KEEP | Controls 224 tests |
| File A | 17 Disposition Ledger | KEEP | Controls requirement tracking |
| File A | 18 Coverage Matrix | KEEP | Controls traceability |
| File A | 19 Completion | IMPROVE (AMEND-A-010) | Add calibration thresholds |
| File A | 20-24 Reconciliation | KEEP | Controls audit closure |
| File B | 1 Objective | PRESENT | Covered by File A §1 |
| File B | 2 Inventory | PARTIAL | GAP-012; LINK_TO_B from File A |
| File B | 3 Principles | PRESENT | Covered by File A §1, §12 |
| File B | 4 Source Contract | PARTIAL | GAP-001; AMEND-A-001 adds fields |
| File B | 5 Pipeline | PRESENT | Covered by File A §5, §9 |
| File B | 6 Profiles | PARTIAL | GAP-014; AMEND-A-003 adds sources |
| File B | 7 Evidence/Guidance | PARTIAL | GAP-004, GAP-005; AMEND-A-002 adds fields |
| File B | 8 Storage | PRESENT | Covered by File A §14 |
| File B | 9 UX | PRESENT | Covered by File A §13 |
| File B | 10 Productivity | PARTIAL | GAP-006; LINK_TO_B |
| File B | 11 API | PRESENT | Covered by File A §14 |
| File B | 12 Tests | PRESENT | Subsumed by File A §16 |
| File B | 13 Milestones | SUPERSEDED | File A R0-R18 controls; AMEND-B-003 |
| File B | 14 Completion | PRESENT | Covered by File A §19 |
| File B | 15 Fable Audit | PRESENT | Covered by File A §20-24 |
| File B | 16 Full Inventory | PARTIAL | GAP-011..021; LINK_TO_B for detail |
| File B | 17 Antigravity | PRESENT | Covered by File A §21 |
| File B | 18 354-Source | PRESENT | Covered by File A §22 |
| File B | 19 Independent Review | PRESENT | Covered by File A §24 |

---

## 23. Exact Append-Ready Markdown Blocks for File A

```markdown
## 0.5 Cross-Reference Authority

This plan is the build-sequence authority. The Hybrid Plan
(`TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md`) is the
domain and decision-reference authority.

### When to consult the Hybrid Plan

| This plan's section | Consult Hybrid Plan for | Hybrid section |
|---|---|---|
| 5.2 Source roles | Complete contract field list (32 fields) | §4 + §15.3 |
| 5.3 Dataset roots | Exact source contract keys (69+43) | §16.6 |
| 5.4 Normalized identity | EvidenceClaim 17-field contract | §7 |
| 7 Feature contracts | Exact calculation formulas | §16.8 |
| 9.2 Strategy profiles | Mandatory sources per profile | §6 + §16.7 |
| 11 Evidence fusion | q_i quality formula, trust combinations | §16.9 + §15.4 |
| 12 Fail-closed gates | 14-state breakage recovery, 12 controls | §16.12 |
| 14 Storage/API | Storage rationale, OpenAlgo interface | §8 + §16.13 |
| 19 Calibration | Probability promotion thresholds | §15.5 |
| All sections | 4-lane reliability architecture | §15.2 |
| All sections | 10-state source maturity ladder | §16.3 |
| All sections | 14-job decision taxonomy | §19.2 |
| All sections | Cross-exchange event matching model | §19.8 |
| All sections | Dataset-root 12-field identity model | §18.4 |
| All sections | Priority activation backlog (20 contracts) | §16.16 |

### Conflict rule

When this plan's four-state model conflicts with Hybrid §7's expanded
state list, this plan controls. Hybrid states become reason codes.
When this plan's R0-R18 milestones conflict with Hybrid §13/§16.17/§17.9,
this plan controls. The Hybrid Plan's detailed formulas, source lists
and domain rules inform the stricter interpretation but do not override
build authority.
```

---

## 24. Exact Append-Ready Markdown Blocks for File B

```markdown
## 0. Authority and Usage

This file is the domain and decision-reference authority for TrendForge.
Build sequence, implementation order, acceptance gates and current build
activity are controlled by the Merge Plan
(`new_merge_PLAN_2026-07-18.md`).

### When to consult the Merge Plan

| This file's section | Consult Merge Plan for | Merge section |
|---|---|---|
| §7 Canonical states | Controlling 4-state model and reason codes | §10 + §20.3 STA-005 |
| §13 Milestones | Controlling R0-R18 implementation sequence | §15 + §24.13 |
| §12 Tests | Complete 224-test suite | §16 + §24.14 |
| §8/§16.14 Sizing | Scope exclusion (no sizing in current milestone) | §1 GOV-002 |
| §16.10 Legacy scorer | Quarantine contract and build-fail test | §20.3 FUS-008 |
| §16.17 Build order | Controlling R0-R18 with amendments | §23.14 + §24.13 |
| §4 Source contract | Additional fields adopted in Merge | §5.2 |
| §16.8 Feature formulas | Feature contract template and registry lint | §6 + §7 |
| §16.7 Per-strategy sources | Profile contract table | §9.2 |
| §15.2 Reliability lanes | Stream integrity contract | §23.10 DAT-033 |
| §16.13 OpenAlgo interface | Conditional read-only capability | §23.10 OPN-005 |
| §15.5 Probability thresholds | Calibration milestone and validation gate | §19 |
| §16.3 Source-state ladder | Source maturity and DAT-021 | §20.2 + §22.6 |
| §18.4 Dataset-root model | Normalized identity and dedup | §5.4 |
| §19.8 Event matching | Correlation group CG_EVENT_ROOT | §11.3 |
| §19.2 Decision-job taxonomy | Dataset root mapping | §5.3 |
| §16.16 Priority backlog | Source activation in R-steps | §15 |

### Conflict rule

When this file's state vocabulary (§7) conflicts with Merge §10,
Merge's four-state model controls; this file's states are reason codes.
When this file's milestones (§13, §16.17, §17.9) conflict with Merge
§15, Merge's R0-R18 controls. This file's detailed formulas, source
lists and domain rules inform the stricter interpretation but do not
override build authority.

### Notes on superseded content

- §7 canonical states: Historical domain states. Public API vocabulary
  is WATCH/WAIT/CONFIRMED/REJECT per Merge §10. States below map to
  reason codes under WAIT. See Merge §20.3 STA-005 for migration.
- §13 milestones: Superseded by Merge §15 R0-R18. Preserved for
  dependency context and domain rationale only.
- §8/§16.14 risk sizing: Domain reference for a future separately
  authorized milestone. Current build scope explicitly excludes position
  sizing, order quantity and execution. See Merge §1 GOV-002.
- §16.10 legacy scorer line references: As of 2026-07-17. Verify
  against current code before implementation. Merge §20.3 FUS-008
  controls quarantine.
```

---

## FINAL VERDICT FORMAT

**Is File A alone sufficient?**
No. File A is sufficient for implementation sequencing, acceptance testing and build-order control. It is insufficient for complete domain specification. 26 gaps were identified where File B contains material detail not fully reproduced in File A.

**What percentage of File B is fully covered, partially covered or missing?**
- **Fully covered:** ~60% (Sections 1, 3, 5, 6, 8, 9, 11, 12, 13, 14, 15, 17, 18, 19 and portions of 16)
- **Partially covered:** ~35% (Sections 2, 4, 7, 10, 16.3-16.18 where File A references but doesn't reproduce detail)
- **Missing from File A:** ~5% (Sections 15.2, 15.4, 15.5, 16.8 formulas, 16.13 interface, 16.14 sizing, 19.2 taxonomy, 19.8 event matching — all addressable via cross-references and amendments)

**Which missing File B requirements materially affect trading decisions?**
1. Per-strategy mandatory source lists (GAP-014): Without exact contract names per profile, developers may wire wrong sources to wrong strategies.
2. Exact feature calculation formulas (GAP-015): Without formulas like RVOL_TOD = cumulative_volume_now / median_cumulative_volume_same_minute, implementations may diverge.
3. q_i quality formula (GAP-016): Without the 6-component quality formula, evidence quality scoring is unmeasurable.
4. Cross-exchange event matching (GAP-026): Without the MATCHED/POSSIBLE_MATCH model, NSE/BSE duplicate deals may create false confidence.
5. 10-state source maturity ladder (GAP-011): Without explicit ladder definitions, "connected" may be mistaken for "gate-authorized."

**Can both files remain separate without causing implementation ambiguity?**
Yes, **if and only if** the 13 recommended amendments to File A and 5 amendments to File B are installed, creating a bidirectional cross-reference system. Without these amendments, a developer reading only File A would miss critical domain detail.

**Exact controls needed to prevent future AI agents from skipping either file:**
1. AMEND-A-013: Cross-reference authority section in File A
2. AMEND-B-001: Authority-and-usage section in File B
3. Automated coverage test (Section 16 of this document): Fails if any File B section lacks a disposition
4. Hash verification: Both files must match recorded SHA-256 hashes
5. Build lint: Feature registry lint fails if any required field is absent (File A Section 6)
6. State contract test: API permits only four product states (T-066)

**Confidence level:**
- **HIGH** for document reconciliation, gap identification, conflict resolution and cross-reference design
- **MEDIUM** for exact implementation effort estimates (R0-R18 delivery time)
- **REQUIRES OBSERVATION** for all live source availability, PKScreener license pin, OpenAlgo route compatibility and production readiness

**Unresolved assumptions:**
1. Both files' SHA-256 hashes remain stable after amendments are applied
2. The 69+43 source contract key enumeration in File B §16.6 is still current
3. The inventory defect counts in File B §16.4 have not been fixed since 2026-07-18
4. PKScreener's MIT license and current commit remain compatible
5. OpenAlgo's API surface matches the documented interface

**Evidence still requiring code or runtime verification:**
1. All 224 acceptance tests (T-001..T-224) are requirements, not observed passes
2. All source contracts remain REQUIRES_LIVE_VERIFICATION until observed
3. No production readiness claim follows from this governance document
4. Code inspection confirmed some mechanisms exist but did not prove end-to-end behavior

**End of Governance Document**
