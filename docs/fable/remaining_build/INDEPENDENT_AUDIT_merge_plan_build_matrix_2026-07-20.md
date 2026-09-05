# Independent Implementation Audit
## Merge-Plan Completeness vs Code (`new_merge_PLAN_2026-07-18.md`)

**Date:** 2026-07-20  
**Plan under review:** `D:/TrendForge/docs/fable/new_merge_PLAN_2026-07-18.md`  
**Status authority (summary):** `docs/BUILD_STATUS.md` (2026-07-20 merge-plan audit)  
**Proof authority:** `docs/VALIDATION.md` (2026-07-20 merge-plan audit)  
**Method:** Requirement extraction from plan §15, §17, §24.13 against `backend/`, `frontend/`, tests, and observed API/UI.  
**Authority level:** Preserved review evidence. Not future-plan authority. Not production-ready claim.

### Method rules (from plan and AGENTS)

- Classification: KEEP / ADD / IMPROVE / POSTPONE / REJECT (from plan dispositions).
- Status: IMPLEMENTED / PARTIAL / MISSING / POSTPONED / REJECTED.
- Five-point check for accepted work: code exists; connected to runtime; reaches correct API/UI; failure/stale behavior tested; runtime observed.
- Not implemented when only a class, endpoint name, fixture, parser invocation or bare HTTP 200 exists.

### Executive verdict

| Scope | Status |
|---|---|
| Plan §24.13 Q5-R0 through Q5-R7 | IMPLEMENTED at approved research/fixture ceilings |
| Plan §15 R0 through R18 full vertical | PARTIAL — Q5 subset only |
| Production selection / durable Q5 history / live CONFIRMED | MISSING |
| PST-* / REJ-* | POSTPONED / REJECTED as planned |

Observed proof (2026-07-20): 158 focused Q5 backend tests passed; frontend 135/135; fixture and capability routes HTTP 200 with fail-closed flags. See VALIDATION.md.

---

## 1. Q5 milestone matrix (§24.13)

| Requirement ID | Plan section | Classification | Expected module | Actual file | API or UI location | Storage location | Test name | Observed result | Status | Gap or blocker |
|---|---|---|---|---|---|---|---|---|---|---|
| Q5-R0 | §24.13 | KEEP | Contract freeze docs | Plan + BUILD_STATUS Q5-R0 | Docs only | N/A | Plan IDs PK-019, API-019, FUS-011, STA-007, DOC-ERR-001, TRC-056 | Frozen; no production claim | IMPLEMENTED | Docs only; no runtime change intended |
| Q5-R1 | §24.13 / §15 R1 | ADD | Source/result/identity/PIT + 4-state DTO | `selection/contracts.py`, `selection/fixtures.py` | `GET /api/v1/selection/fixtures/q5-r1` | In-memory fixture | `test_q5_selection_contracts.py` | HTTP 200; NO_EARLY_CONFIRMED; WATCH/WAIT/REJECT | IMPLEMENTED | No durable facts DB |
| Q5-R2 | §24.13 / §15 R3 | ADD | Family resolver, zero corroboration | `selection/resolver.py`, `r2_fixtures.py` | `GET …/q5-r2` | In-memory | `test_q5_family_resolver.py` | HTTP 200; WATCH_WAIT_REJECT_ONLY | IMPLEMENTED | Not full live S0–S3 pipeline |
| Q5-R3 | §24.13 / §15 R5 | ADD | Closed-bar structure pack | `selection/structure.py`, `r3_fixtures.py` | `GET …/q5-r3` | In-memory | `test_q5_closed_bar_structure.py` | HTTP 200; one EOD CONFIRMED; fixtureOnly; productionAuthorized=false | IMPLEMENTED | EOD research fixture only |
| Q5-R4 | §24.13 / §15 R6+R11/R12 slice | ADD | Bounded enrichment, options, MCX gates | `enrichment.py`, `options_domain.py`, `mcx_contracts.py`, `r4_fixtures.py` | `GET …/q5-r4` | In-memory | `test_q5_bounded_enrichment.py` | HTTP 200; UNKNOWN_EXPLICIT_NO_MCX_CONFIRMED | IMPLEMENTED | No live MCX master / options feed |
| Q5-R5 | §24.13 / §15 R4+R7 | ADD | Finite offline PK harness | `scanners/pk_compatibility.py`, `pk_fixture_worker.py` | No production route; CLI `python -m trendforge_api.scanners` | Fixture artifacts | `test_q5_pk_compatibility.py` (T-191/192/193) | 0 shadow routes; REGISTERED_NOT_ACTIVE; votingWeight=0 | IMPLEMENTED | Upstream pin not VERIFIED; native catalog not production-promoted |
| Q5-R6 | §24.13 / §15 R9+R16 partial | ADD | Inspector, history, PIT, drift | `history_validation.py`, `pit_path.py`, `r6_fixtures.py`; FE `q5-contract.js`, `app.js`, `index.html` | `GET …/q5-r6` + primary radar/inspector | In-memory only | `test_q5_history_validation.py`; FE acceptance | HTTP 200; performance/probability hidden; validation locked | IMPLEMENTED (ceiling) | Durable state/PIT store MISSING |
| Q5-R7 | §24.13 / §15 R17 partial | KEEP | OpenAlgo read-only boundary | `openalgo_client.py`, capability in `main.py` | `GET /api/v1/integrations/openalgo/capability` | Config/env | `test_q5_openalgo_boundary.py` (+ client/adapter) | State ABSENT; intradayConfirmationAllowed=false | IMPLEMENTED (boundary) | Live feed/replay integrity unverified |

### Five-point summary

| Check | R0 | R1 | R2 | R3 | R4 | R5 | R6 | R7 |
|---|---|---|---|---|---|---|---|---|
| Code exists | Docs | Y | Y | Y | Y | Y | Y | Y |
| Connected to runtime | N/A | API | API | API | API | CLI (by design) | API+UI | API |
| Correct API/UI | N/A | Fixture | Fixture | Fixture | Fixture | No prod API | Fixture+dashboard | Capability |
| Failure/stale tested | N/A | Y | Y | Y | Y | Y | Y | Y |
| Runtime observed | Hash restore | HTTP 200 | HTTP 200 | HTTP 200 | HTTP 200 | CLI+tests | HTTP 200+FE | HTTP 200 |

---

## 2. Full plan R0–R18 matrix (§15)

| Requirement ID | Plan section | Classification | Expected module | Actual file | API or UI | Storage | Test / evidence | Observed result | Status | Gap or blocker |
|---|---|---|---|---|---|---|---|---|---|---|
| R0 | §15 | MERGE/ADD | Contract freeze | Plan docs; partial code contracts | Docs / existing app boots | N/A | Contract IDs; Q5-R0 | App boots; freeze documented | PARTIAL | DAT-010/011 incomplete |
| R1 | §15 | ADD | Selection DTO + radar | Q5 fixtures + R6 FE | q5-r1, q5-r6 UI | Fixture | Q5 R1/R6 + FE 135 | 8 questions; safe labels | IMPLEMENTED (fixture) | Live production DTO not authorized |
| R2 | §15 | ADD | S0–S3 cheap live pipeline | Source adapters + partial selection | Legacy context/scanner APIs | Partial | Source tests; not one Q5 run | Fragmented | PARTIAL | No single production S0–S3 selection vertical |
| R3 | §15 | ADD | Family resolver | `selection/resolver.py` | q5-r2 | Fixture | family_resolver tests | Caps/conflicts | IMPLEMENTED (fixture) | Maps to Q5-R2 |
| R4 | §15 | ADD | PK0 pin + early PIT/delist | `scanners/pk_compatibility.py` | CLI | Fixture | pk_compatibility 31 | Offline pin/harness | PARTIAL | Full delist/PIT universe set incomplete |
| R5 | §15 | ADD | Structure pack + first CONFIRMED | `selection/structure.py` | q5-r3 | Fixture | closed_bar_structure | One EOD CONFIRMED fixture | IMPLEMENTED (fixture) | Maps to Q5-R3; not production |
| R6 | §15 | ADD | Shortlist enrichment | `selection/enrichment.py` + R4 | q5-r4 | Fixture | bounded_enrichment | Budgeted jobs | PARTIAL | Live surveillance/events/FO wiring incomplete |
| R7 | §15 | ADD | Isolated PK shadow/CLI | scanners package | CLI only | Fixture | pk tests | Isolated; no state vote | IMPLEMENTED | Maps to Q5-R5 |
| R8 | §15 | ADD | Native core registry | structure only | — | — | structure tests only | No full catalog | MISSING / PARTIAL | Breakout/NR/volume/trend catalog incomplete |
| R9 | §15 | ADD | Lifecycle history; ORB/VWAP | `history_validation.py` | q5-r6 inspector | In-memory | history_validation | History reconstructs | PARTIAL | ORB/VWAP confirm needs verified bars |
| R10 | §15 | ADD | Pipe DSL + family caps | — | — | — | — | — | MISSING | No pipe engine/API/UI |
| R11 | §15 | ADD | RS/delivery + MCX master | `mcx_contracts.py` fixtures | q5-r4 | Fixture | R4 MCX tests | WAIT without master/local | PARTIAL | Live MCX master not production-promoted |
| R12 | §15 | ADD | Options timeline/walls | `options_domain.py` | q5-r4 | Fixture | R4 option tests | Explicit UNKNOWN/WAIT | PARTIAL | No production options timeline API |
| R13 | §15 | ADD | Remaining scanners | — | — | — | — | — | MISSING | |
| R14 | §15 | ADD | CA/sponsor PK reconciliation | Partial CA modules | Legacy CA APIs | Partial | CA tests | Not PK-join path | PARTIAL | |
| R15 | §15 | ADD | Scanner Lab UI | — | No FE Scanner Lab | — | — | — | MISSING | |
| R16 | §15 | ADD | PIT before performance UI | `history_validation.py` + FE lock | q5-r6; hidden validation | Fixture | R6 + FE canShowPerformance | Lock works; no prod charts | PARTIAL | No production PIT dataset |
| R17 | §15 | KEEP | OpenAlgo RO after integration | `openalgo_client.py` | capability API | Env | openalgo boundary | ABSENT; no orders | PARTIAL | Live shadow not observed |
| R18 | §15 | ADD | Model governance / upgrades | Drift contracts in R6 | Fixture inspector | Fixture | drift tests | Contracts only | PARTIAL | Upgrade promotion workflow not operational |

---

## 3. Core requirement-family matrix (§17)

| Requirement ID | Plan section | Classification | Expected module | Actual file / evidence | API or UI | Storage | Test name | Observed result | Status | Gap or blocker |
|---|---|---|---|---|---|---|---|---|---|---|
| GOV-001..006 | §3, §17 | KEEP/IMPROVE | Research-only boundary | Fixture flags; FE evidence-strength label | Q5 DTOs + FE | N/A | Q5 + FE | productionAuthorized=false; executable=false | IMPLEMENTED (ceiling) | Production-ready correctly not claimed |
| STA-001..004 | §10 | MERGE/ADD | Four states; gate reasons | `contracts.py`, resolver, history | Radar chips | Fixture history | R1–R6 | Four public states | IMPLEMENTED (fixture path) | Durable history missing |
| STA-007 | §24 | IMPROVE | WAIT vs hard REJECT | resolver + history_validation | Gates in DTO | Fixture | R2/R6 | Recoverable→WAIT; hard→REJECT | IMPLEMENTED | |
| FUS-001..008, FUS-011 | §11, §20 | IMPROVE | Families; corr caps; zero bonus | `resolver.py` | Family supports | Claim DTO | R2 | Corroboration 0; caps | IMPLEMENTED (resolver) | Not sole legacy rank path |
| DAT-001..005 | §5–6 | KEEP/ADD | Roles, empty≠fail, hash, timestamps | `source_contracts.py` + selection | Source health + fixtures | Archives | Source + Q5 | Enforced on Q5 proofs | PARTIAL | Not universal on every live path |
| DAT-006..009,013,014 | §5, §12 | ADD | PIT identity, CA, calendar, completeness, IDs | Partial across modules | Mixed | Partial | Mixed | Strong in fixtures | PARTIAL | |
| DAT-010 | §6 | ADD | Feature registry lint | No central production lint | — | — | Not full suite | — | PARTIAL / MISSING | Production-rank registry lint not repo-wide |
| DAT-011 | §7.4 | ADD | Pinned indicator engine | Not Q5-delivered pin | — | — | Partial/absent | — | MISSING | R0 residual |
| DAT-015 | R0 | ADD | MWPL owner freeze | Parsers/inventory pieces | Safety paths | Inventory | Surveillance tests | Partial ownership | PARTIAL | Dated artifact promotion not proven as Q5 freeze |
| DAT-016 | §5.3, R4 | ADD | MCX master | `mcx_contracts.py` | q5-r4 | Fixture | R4 | Gates enforce WAIT | PARTIAL | Live master missing |
| DAT-017 | §12, R17 | ADD | Broker bar integrity | OpenAlgo client | capability | Env | OpenAlgo tests | Boundary only | PARTIAL | Live stream integrity not observed |
| SEL-001..010 | §9 | IMPROVE | S0–S9 pipeline | Pieces only | Fixture verticals | Mixed | Fragmented | Not one product run | PARTIAL | |
| PRF-001..007 | §9.2 | KEEP | Market/horizon profiles | Ceiling semantics | Fixtures | — | Fixture ceilings | Not full profile engine | PARTIAL | |
| UI-001..006, UI-010 | §13, R6 | IMPROVE | Radar + inspector | `index.html`, `q5-contract.js`, `app.js` | Primary dashboard | — | FE 135; R6 | 8 answers; inspector; history | IMPLEMENTED (fixture-backed) | Live non-fixture payload not authorized |
| UI-007 | §13, R15 | ADD | Scanner Lab | — | — | — | — | — | MISSING | |
| UI-008 | §13 | ADD | Failure + state history views | Q5 inspector/history | q5-r6 UI | Fixture | R6 + FE | Present | IMPLEMENTED (fixture) | |
| UI-009 | §13, R16 | ADD | PIT performance views | FE canShowPerformance lock | Hidden | — | R6 + FE | Locked for fixture | IMPLEMENTED as lock; charts MISSING | Correct |
| STO-001..006,009..011,013,014 | §14.1 | MERGE/ADD | Fetch/facts/bars/scanners | Legacy storage modules | Legacy APIs | SQLite/parquet partial | Mixed | Domain-dependent | PARTIAL | |
| STO-007,008,012 | §14.1 | ADD | Candidate projection, state events, PIT outcomes | In-memory Q5 contracts only | q5-r6 | **Not durable** | R6 | Reconstructable in fixture | PARTIAL | Migration required |
| API-001..010,017,018 | §14.2 | IMPROVE | Scans, candidates, scanners, pipes… | Mostly missing Q5 prod APIs; legacy `/api/*` | Partial | Partial | Partial | Fixture GETs exist | PARTIAL | No POST selection-scan vertical |
| API-011..016 | §14.2 | ADD | Four-state, null reason, labels, completeness | Q5 DTO contracts | Fixture responses | Fixture | Q5 contract tests | Present on fixtures | IMPLEMENTED (fixture DTO) | Production scan DTO incomplete |
| API-019 | §24 | ADD | No shadow PK production routes | main route inventory | — | — | `test_production_route_inventory_contains_no_pk_shadow_routes` | 0 routes | IMPLEMENTED | |
| OPN-001..004 | §14, R17 | KEEP | Disabled RO OpenAlgo | openalgo_client + capability | capability GET | Env | boundary tests | ABSENT; no order surface | IMPLEMENTED (boundary) | Live RO feed not validated |
| PK-001..008,016,019 | §3, §24 | KEEP/ADD | Pin, harness, shadow non-authority | scanners package | CLI | Fixture | 31 PK tests | Offline only | PARTIAL | Full catalog/pipes/lab missing |
| PK-009..015 | §3 | KEEP | Pipe, reconcilation, lab, upgrades | — | — | — | Partial negatives | AI/profit cannot rank (tested) | PARTIAL / MISSING | Lab/pipes/upgrade workflow open |
| TRC-001..005, TRC-056 | §0, §18, §24 | KEEP | Traceability | Plan + audit restore | Docs | Docs | Q5-R0 hash | Audit recovered | IMPLEMENTED (docs) | |
| PST-001..008 | §8 | POSTPONE | GEX, depth, LLM, multi-terminal… | Not in decision path | — | — | — | — | POSTPONED | As planned |
| REJ-001..012 | §8 | REJECT | Probability, execution, fake zeros… | Enforced by contracts | — | — | Multiple adversarial | Excluded | REJECTED | Keep enforcing |

---

## 4. Acceptance-test band status (§16 / §24.14)

| Test band | Plan IDs | Repo evidence | Status |
|---|---|---|---|
| Transport/schema | T-001..010 / T-170..175 | Source runtime/hardening (partial) | PARTIAL |
| Time/identity/CA | T-011..020 / T-176..180 | CA, candle lineage, Q5 structure | PARTIAL |
| Correlation/features | T-021..035 / T-181..184,212 | Resolver + options/OI Q5 groups | PARTIAL |
| Authority/safety | T-036..048 / T-185..190,197,200,208-211 | Q5 gates + source authority tests | PARTIAL |
| PK/shadow | T-049..058 / T-191..193,201-203 | `test_q5_pk_compatibility.py` | IMPLEMENTED (offline ceiling) |
| Backtest/UI/OpenAlgo | T-059..070 / T-204..209 | R6 PIT contracts + FE hide + OpenAlgo | PARTIAL |

Not every plan test ID has a 1:1 named pytest. Q5 packs cover their adversarial ceilings well.

---

## 5. Explicit non-claims

1. Durable Q5 history/PIT storage is not implemented.
2. Production selection scans are not implemented.
3. Live-universe CONFIRMED with production authorization is not implemented.
4. Intraday CONFIRMED is blocked (`NO_INTRADAY_CONFIRMED`).
5. MCX CONFIRMED is blocked.
6. PK production vote/sidecar/shadow routes are correctly absent — not a gap.
7. Scanner Lab, pipe DSL, full native PK catalog are missing.
8. Performance/probability UI is correctly locked — not a pass for charts.
9. Execution/OMS is rejected and absent.

---

## 6. Recommended next work

1. Durable selection storage (migration approval) for STO-007/008/012.  
2. Live S0–S3 selection run bound to official sources + completeness.  
3. R8 native core scanners under family caps.  
4. R10 pipes, then R15 Scanner Lab.  
5. R17 live OpenAlgo only after integrity/replay tests.  
6. R16 production PIT dataset before any performance UI.

---

## 7. Provenance

| Artifact | Role |
|---|---|
| `docs/fable/new_merge_PLAN_2026-07-18.md` | Future plan authority (requirements) |
| `docs/BUILD_STATUS.md` §2026-07-20 merge-plan audit | What is built (summary) |
| `docs/VALIDATION.md` §2026-07-20 merge-plan audit | Observed proof |
| This file | Full matrix review evidence |

No production-ready claim follows from this document.
