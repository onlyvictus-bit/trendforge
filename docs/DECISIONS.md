# Decisions

## D-069 Plan audit: grant design is prerequisite; exact match/source lists pinned - 2026-09-04

Tester audit of the three-blocker plan (D-068) found four gaps, fixed in
`THREE_BLOCKERS_BUILD_PLAN_2026-09-04.md`: (1) R5 hash-match compares seven
fields, not five — all named; (2) gate_permission has no grant path in code,
so a human-review grant record/contract (fields + approver + audit trail) must
be designed before activation is achievable at all; (3) the five R2-B
confirm-path source keys are pinned with per-window re-checks; (4) fixture
inputs are for unit tests only, prod paths use observed evidence only, with a
4-row operator approval matrix and effort CIs. Fail-closed rollback is the
default for all three parts: no forced flips, ever.

## D-068 Three-blocker build plan adopted; checkpoint confirmed in normalized store - 2026-09-04

Adopts `docs/fable/remaining_build/THREE_BLOCKERS_BUILD_PLAN_2026-09-04.md`
(sequencing, ownership, gates) with detail in
`docs/fable/remaining_build/PRICE_BAND_TECHNICAL_ZONES_BUILD_PLAN_2026-09-04.md`.
Boundary-source decision: calculated geometry from proven inputs (deep-plan
council: 78%, grade A); member-feed download and indefinite WAIT rejected.
Canonical-surface rule: the content-addressed normalized store
(`data/market_data/`, read via `store.latest_for`) is the gate-truth for
restriction evidence; SQLite parse tables are archive only. Confirmed pinned
hashes: price-bands 3,517 rows @2026-09-02, ESM 290 rows @2026-09-03, auction
NIL valid-empty @2026-07-09. R5 and activation gaps are data-ops/governance
consequences, not code defects; no R5 code change is authorized by this plan.

## D-067 Restriction acquisition reuses the canonical collector/store - 2026-09-03

ESM, price bands and periodic-call-auction data are normal contracts in the
existing registry, transport/resolver, parser and immutable last-good store.
The unified tradability gate reads that canonical normalized store first; it
does not maintain a second downloader or source database. Corrupt canonical
identity fails as MALFORMED rather than silently substituting older data.

The registry pin is 126 jobs. ESM is weekly/change-aware, price bands are daily
classification data, and the auction list is quarterly/change-aware with
explicit `NIL` accepted as valid empty. Price-band percentage alone cannot
prove proximity to a lower/upper exchange limit, so exact geometry remains
WAIT. These contracts are veto/readiness inputs only and do not vote, activate
CONFIRMED or authorize execution.

## D-066 Tradability is one fail-closed veto/readiness gate - 2026-09-03

One backend-owned gate evaluates symbol tradability before S7 state assignment.
Components retain separate source, freshness, parser, content-hash and reason
lineage, but collapse by strict precedence `REJECT > WAIT > PASS`. A PASS is
not evidence and contributes no vote. S8 stores the exact gate hash and
component result so later replay cannot silently use different restrictions.

NSE intraday, NSE swing/event and MCX use separate policies. Missing required
ESM, band, halt/auction or MCX mechanics remain WAIT; explicit suspension,
T2T intraday, active F&O ban, locked band, halt or delivery/tender violation
may REJECT. Unverified endpoint registration is not accepted as source truth.


## D-065 Strategy profiles own named source groups, not source activation - 2026-09-02

PRF-001 through PRF-007 use one typed registry of mandatory, confirmation and
veto source groups. ALL_OF and ANY_OF semantics are explicit. Compiler
registration is shown for contract completeness but can never substitute for
fresh populated data, lineage, evidence-family acceptance or gate authority.
Unavailable OpenAlgo intraday bars keep PRF-001/002 incomplete; delayed global
and ownership feeds remain context only.

## D-064 R18 is durable governance with a PIT approval ceiling - 2026-09-02

R18 uses a typed deterministic evaluator plus explicit append-only SQLite governance records. It does not add a live trainer, online learner, automatic promotion service or second decision engine. Model identity binds dataset, features, formulas and model hashes. The production evaluator must prove its dataset hash exists in R16 storage. Human review loads persisted immutable model/evaluation evidence and is required for promotion, while drift may automatically demote and identify the previous signed champion for deterministic rollback.

R18 may be implemented and fixture-tested while R16 is PIT_NOT_APPROVED, but APPROVE must fail and every public projection remains MODEL_NOT_APPROVED. Migration 0014 is separately approval-gated and never auto-applied by a GET. Probability, win rate and performance remain hidden until independent PIT/OOS approval.

## D-032 Cash research path A1â€“C1 without activation - 2026-08-15

The NSE cash research pipeline A1â€“C1 is accepted as File A implementation
evidence under Â§25.20.1 / Â§25.25 ceilings:

- A1 stages last-good cash as `SourceResult` (no `NormalizedFact`).
- A2 creates identity facts and S0/S1 gates; ban veto requires proven artifact.
- A3 emits Â§25.25.4 WATCH discovery reasons (not `FTR-018`, not CONFIRMED).
- A4 stores immutable RAW sessions and PIT CA vintages (CROSS-020 adjusted series).
- A5 index context and CA integrity cannot vote.
- A6 enriches WATCH shortlist with futures OI only (no option/futures mix).
- C0 owns `can_rank` / `can_veto` / `can_unlock_confirmed` (always false for confirm).
- B leaves MWPL as `MWPL_MISSING` unless a percentage artifact is proven.
- C1 attention-ranks only when C0 allows cash `can_rank` (WATCH ceiling).

This does **not** set `sourceActivationReady`, does **not** authorize live
CONFIRMED or quantity, and does **not** complete Final Merge FMR-001/002.
R0-B `canVote` remains false. Named activation is a later R2-B milestone.

## D-031 R0-B field review and R1 WAIT persistence spine - 2026-08-15

R0 residual work is split by File A Â§25.20.1. **R0-A** (compiler honesty) is
closed at H1A0 6/6 on pin `f1abcdceâ€¦`. **R0-B** (first official cohort) is
field-reviewed with genuine parser-backed fields plus named waivers for
shared retry/breaker and the missing MWPL percentage artifact; cohort report
`provenCount=0` and every member `canVote=false`. **R0-C** remains
quarantined. Review completion does not authorize gates.

R1 storage spine is allowed at the STO-006/007/008 ceiling without activation:
`selection_scan_runs`, `selection_candidates`, `selection_state_events`.
`POST /api/v1/selection/live/refresh` may persist WAIT batches only.
`GET /api/v1/selection/live` returns the latest stored run when present.
Quantity fields stay rejected. Live CONFIRMED, full voting-claim streams, and
R2 named activation remain closed until their own milestones.

## D-036 CROSS-001-v2 overlap review and workbook re-pin - 2026-08-15

The current inventory workbook hash
`f1abcdce2b451b4ded9d9e9c8eb6bd63fae82853803f60bef60a1651dd52eb0b`
replaces the 2026-07-23 pin only after three new overlap groups were
reviewed:

- NSE `bulk.csv` is one daily bulk-deal dataset under a named contract and a
  generated inventory identity (`SAME_DATASET_ALIAS`).
- The AMFI portfolio page is one landing URL for a directory job and a
  delayed holdings job (`DISTINCT_SHARED_ENDPOINT`).
- The MCX delivery-reports page is one landing URL for delivery pressure
  and warehouse inventory (`DISTINCT_SHARED_ENDPOINT`).

H1A0 6/6 on this pin proves compiler overlap acceptance only. It does not
rebuild CROSS-002, activate sources, or authorize CONFIRMED. The live
176-key union versus the 129-key CROSS-002 review remains a separate
residual.

## Historical Source-Catalog Reuse Decision - 2026-07-17

The twelve verified routes use the existing `AsyncEndpointClient`, source
catalog, immutable raw archive and endpoint-fetch ledger. TrendForge does not
add copied standalone downloader scripts for the same endpoints.

The CFTC SODA endpoints are capped at latest-first 500 rows because the
previous 5,000-row request could exceed the 10 MB raw-response guard. CFTC,
NSDL and index derivatives are retained as delayed or market-context evidence;
they cannot create a symbol-level intraday CONFIRMED state. NSE shareholding can
populate candidate ownership fields with its reported date, but is not live
flow proof. This keeps the `RESEARCH_ONLY` outcome honest while retaining
lineage for later parser and gate work.

## D-025 Canonical Inventory Compiler And Source-Activation Ceiling

`SOURCE_LINK_INVENTORY_MASTER.xlsx` remains the immutable human inventory.
TrendForge compiles it into a normalized migration view containing endpoint,
dataset-root, source-contract, lineage, maturity and decision-job records. The
compiler must fail explicitly for missing, empty or malformed inputs and must
preserve raw defects rather than silently rewriting the workbook.

Descriptive status text, URL reachability, an HTTP 200 response, a parser, or a
runtime catalog key cannot promote maturity. Promotion requires contiguous,
source-specific proof. Missing mirror/resolver identity, authority caps or any
required source-contract field remains `UNSPECIFIED` and blocks activation.
Runtime source coverage and activation APIs use compiler output rather than an
older fixed link list.

Passing normalized H1A0 checks proves only compiler determinism. It does not
prove source usability, freshness, gate authority or permission to produce
`CONFIRMED`. Current counts must be read from the compiler report: normalized
source identities, living source keys and generated endpoint-lineage identities
are different populations and must not be called one set of "source
contracts." Gate-authorized source count and source activation also come from
observed runtime rather than this decision text.

## D-026 Compiler Output Is The Runtime Gate Authority

Fresh structured parser output is necessary but insufficient for confirmation.
Runtime readiness must also receive `sourceActivationReady=true` and explicit
gate permission from that compiled source contract. If either proof is absent,
the source remains `WAIT_SOURCE_ACTIVATION` or
`WAIT_SOURCE_GATE_PERMISSION`; it cannot become `PASS/CAN_CONFIRM`.

Static replacement maps, descriptive source roles and legacy helper defaults
are non-authoritative. They may explain migration or safe use but cannot grant
permission. Official surveillance and F&O-ban observations remain hard vetoes
even while positive confirmation is globally disabled.

## D-027 Semantic Overlaps Require Exact Typed Resolutions

Free-text workbook notes cannot suppress a semantic-overlap defect. A reviewed
resolution is valid only for one normalized URL and its exact sorted contract
set, with a typed disposition, canonical relationship, evidence basis, version,
review date and the reviewed workbook hash. Wildcards, URL equality alone,
weak alias evidence, changed contract sets, duplicate/conflicting entries or a
changed workbook hash fail closed.

Per-segment prefixes in compound historical rows bind each contract only to its
own URL; the compiler must not create a URL/contract cross-product. Reviewed
aliases, parent/child relationships and distinct datasets sharing an endpoint
remain visible in the report and never grant independent evidence, source
activation, gate permission, quantity, execution or `CONFIRMED`.

## D-028 Final Merge Is A Mandatory Mapped Addendum

`docs/fable/FINAL_MERGE_PLAN.md` is the accepted mandatory product/design addendum for all-source and all-stock research, discovery and PK workflows, the unified options package, Gamma/GEX scenarios, strike/expiry intelligence, open-source calculator boundaries, trader-facing radar/inspector behavior, and FMR-011 Research Paper Lab / governed batch ML.

File A section 25.21 maps `FMR-001..011` aliases into existing `R0-R18` milestones. FMR aliases are traceability/navigation IDs only; runtime code and tests use File A stable IDs. File A remains the only build-sequence, scope, state, permission, ceiling, reject/postpone and acceptance authority. **File B** means only the Hybrid plan (`TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md`). Discovery and Options plans are **detail plans**, not File B and not a second sequence. The coverage CSV must carry every FMR alias so omission becomes visible.

Current runtime code is implementation evidence, not permission to preserve a conflicting flow. Existing fetchers, parsers and storage should be adapted where valid; duplicate state writers, unsafe legacy scores and conflicting paths must be quarantined through their mapped File A milestone rather than silently retained or deleted.

Do not hardcode activation flags into plans; current activation and state ceiling come from observed runtime plus BUILD_STATUS and VALIDATION.

## D-029 Single Build Spine And Detail-Tag Governance

There is one build spine: File A `R0-R18` (plus CROSS/TDG owned by File A). Detail tags `M0-M23`, `T0-T4`, and `PK-A..PK-D` may exist only inside the Discovery Detail Plan (and related product docs) as module/UI labels. Each tag must have an explicit File A owner and FMR open-list. Agents must not choose work by â€œnext Mâ€. Before a mapped vertical, open File A, then every mapped FMR section, then Hybrid sections File A requires, then Discovery/Options detail. Coverage generator governance checks must fail closed when FMR sets diverge, detail tags lack owners, dual-spine phrases reappear, or `___KEEP___` placeholders remain.

## D-030 Professional Mathematics Is A Mapped Research Detail

docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md is retained as a mapped
research mathematics detail reference under File A section 25.22. It does not
create a second build order, state model, score, source permission, quantity or
execution path. File A remains authoritative; Hybrid owns q_i; File A owns
FUS-009; Discovery owns the M-Factor projection; Final Merge and Options own
the detailed option identity, eligibility and formula contracts.

Current CONFIRMED is evidence-based and does not mean calibrated probability
or positive expected value. Probability/EV, finite-horizon first-passage and
covariance-fusion research require point-in-time outcomes, conservative costs,
walk-forward/OOS proof and mapped R16/R18 approval. The architecture stores
only observable price/OI quadrant codes. Buildup, covering, participant identity
and intent are interpretations. Microprice, OFI and calibrated impact remain
unavailable until a verified timestamped order-event source exists.
Dividend-aware Theta and local delta-hedged realized-versus-implied variance attribution are accepted as versioned model outputs under R12/R16, with full equations and assumptions owned by Professional Mathematics section 17.5. They are not directional P&L, observed flow, independent confirmation or guaranteed gamma-scalping profit.

Variance-risk-premium context is accepted only as postponed research context under R12/R16, with R18 governing promotion, drift and demotion. It requires synchronized same-horizon risk-neutral implied variance and a PIT physical expected-realized-variance forecast, plus costs, liquidity and tail-risk controls. `ATM_IV^2 * T` remains a labeled proxy. Fixed VRP thresholds, `IV > RV => sell`, `IV < RV => buy`, and directional claims from backwardation/contango are rejected. Missing or unapproved evidence returns `VRP_UNKNOWN` and cannot authorize state, quantity or execution.
## D-001 Authoritative Specification Location

The requested `TREND_FORGE_MASTER_PLAN.md` is preserved as `archive_markdown_backup_20260710/TREND_FORGE_MASTER_PLAN.md.backup` and embedded verbatim in the canonical documents. SHA-256: `978939b64e3a39f1329e0c19c3c059e3f253bb53b9080d4fa3c107b10d44dc2d`.

Active implementation follows current explicit user instruction, `AGENTS.md`, and `docs/fable/new_merge_PLAN_2026-07-18.md` (File A) for future sequence and stable requirement IDs. `TREND_FORGE_ARCHITECTURE.md` owns full system boundaries, `TREND_FORGE_SOURCE_REGISTRY.md` owns source meaning, the Hybrid plan supplies domain detail through File A Â§0.5/Â§25 pointers, and `docs/fable/FINAL_MERGE_PLAN.md` supplies mandatory product/design detail through File A Â§25.21 FMR mappings. The Final Merge addendum cannot change File A order, states, source/gate authority, acceptance ceilings, no-quantity/no-execution boundaries, or stable implementation IDs. `present.md` and the embedded standalone implementation plan remain historical context and cannot override File A or a later architecture lock.

## D-002 Preserve The Existing Stack

The repository already has a working FastAPI, Pydantic v2, SQLite, Parquet and static browser application with tests. It will be evolved incrementally. React/TypeScript and SQLAlchemy/Alembic were defaults only for an empty repository, so an immediate rewrite would add risk without improving the screening brain.

## D-003 Read-Only V1

The application may import, fetch, scan, rank, explain, alert and journal research evidence. It may calculate risk warnings and no-action reasons, but it cannot produce executable quantity, manage positions, access accounts, or place, modify or cancel broker orders. OpenAlgo remains a later read-only data boundary requiring separate integrity validation and explicit authorization.

## D-004 Source Inventory Is Not Evidence

All saved URLs receive a machine-readable role. A URL cannot unlock `CONFIRMED`. Gate authority requires a contracted artifact, archived bytes, a matching structured parse, correct scope, freshness and symbol evidence.

## D-005 Point-In-Time And Fail-Closed

Unknown is not zero. Old parses cannot be attached to newer artifacts. Mirrored evidence counts once. Data available after the scan cutoff is excluded from decisions and ML features.

## D-006 Documentation Count

The four active root Markdown documents remain `AGENTS.md`, `present.md`, `TREND_FORGE_ARCHITECTURE.md`, and `TREND_FORGE_SOURCE_REGISTRY.md`. Current future implementation order lives in `docs/fable/new_merge_PLAN_2026-07-18.md` (File A); `present.md` section `16. Build Order` and the embedded former implementation plan are retained as historical evidence. Files under `docs/` provide executable maps, decisions, status, validation and traceability and must link to the current authority locations.

## D-007 Causal Eligibility And Independence Penalties

Stage 1 applies the stricter combined interpretation of master-plan rules 42.4 and 42.14. A candidate needs the configured total, configured passing-layer count, top-decile rank, and every default layer floor: CAUSE 2, SPONSOR 4, STRUCTURE 2, FLOW 2. Stage 2 cannot run when Stage 1 is ineligible.

For each shared raw-input key and cross-layer pair, the master penalty `0.3 * min(A, B)` is calculated once from the strongest positive evidence in each layer. Half is charged to each affected layer. This avoids arbitrary double charging while preserving post-penalty layer thresholds and an auditable total.

Stale evidence is capped at 0.4 weight even when no signal-specific decay lambda exists. It may remain context but cannot keep full conviction. Future-dated evidence is a point-in-time hard failure.

## D-008 Candle Correction And Lineage Policy

The natural candle key remains symbol, timeframe, source and timestamp. An identical re-fetch is a no-op. If any stable candle value changes, TrendForge stores old and new payloads and hashes in `candle_revisions`, then updates the canonical row to the corrected value. `fetchedAt` alone is excluded from the content hash so a repeated download does not create a false market-data revision.

Every distinct candle content hash receives one quality record. Partial bars, low completeness and unofficial/synthetic sources remain usable for labeled research but carry `WARN`; invalid OHLC geometry or negative volume is rejected before storage.

## D-009 Structured Evidence Claim Policy

Only normalized rows available at or before the scan cutoff can become causal evidence. Bulk deals, AMFI deltas, structured SEBI transactions and qualifying corporate events retain source key, source row id, source date, observed time, trust, contribution and explanation.

ESOP/allotment/inter-se transfer rows do not become positive sponsor conviction. A single filing may support both CAUSE and SPONSOR only through separate claims sharing the same raw-input key, which activates the independence penalty. Evidence claims do not bypass raw-artifact, parser-freshness, market, safety or execution gates.

## D-010 Harmonic Lifecycle Ordering

Lifecycle outcomes are evaluated chronologically from completion through trigger, targets, invalidation and expiry. Invalidation before trigger is `INVALIDATED`; invalidation after trigger is `LOSS`. When a target and stop are both touched in one OHLC bar and lower-resolution data cannot establish ordering, TrendForge records the conservative `LOSS` outcome rather than assuming a win.

## D-011 Alerts And Journal Remain Manual

General alerts must contain a reason and risk context, not only a symbol. Journal records describe manually recorded research decisions and outcomes. Their request models reject unknown broker-order fields, preserving the v1 read-only boundary.

## D-012 Scheduled Harmonic Identity And Reaction Trigger

A scheduled harmonic identity is the hash of symbol, timeframe, pattern, direction and the timestamp/price/kind of its XABCD anchors. Appending later candles therefore advances the same lifecycle; changing an anchor creates a new pattern identity. If revised post-D candles contradict an already stored sequence, TrendForge returns `CONFLICT_DATA_REVISION` and does not rewrite the earlier point-in-time event.

The master plan defines `TRIGGERED` as confirmation after PRZ reaction but does not prescribe one numeric trigger. The deterministic v1 interpretation places the reaction trigger 10% of the distance from the direction-facing PRZ boundary toward T1. Expiry windows are timeframe-specific and deliberately conservative. These mechanics track research outcomes only and cannot create `CONFIRMED` or broker execution. The PRZ itself is centered around D; representing the whole C-D leg as PRZ was corrected as a geometry defect.

## D-013 Corporate-Action Adjustment And Reconciliation

Corporate actions are evaluated only from observations available by the scan cutoff. Repeated observations from one source resolve to its latest point-in-time version; independent NSE/BSE observations must agree on the effective date and adjustment ratio. Cancellation disagreement or ratio disagreement is `CONFLICT` and blocks price-derived scoring.

Split factors use old shares divided by new shares. Bonus factors use held shares divided by total post-bonus shares. These share-count factors are applied to pre-ex-date OHLC and inversely to volume. Cash dividends use `(pre_ex_close - cash_amount) / pre_ex_close`; rights use TERP from the pre-ex close, entitlement ratio and subscription price. Dividend and rights factors adjust OHLC but not historical volume. A late filing never changes history silently: the scanner emits `REJECT_DATA_INTEGRITY`, and the explicit reconciliation operation writes corrected candles through `candle_revisions`. Merger/reconstruction and incomplete terms remain hard-blocked.

## D-014 BSE Offer Index And XBRL Authority

BSE buyback/takeover list APIs are authoritative discovery indexes but not complete trade evidence. A linked official XBRL document must be archived, safely parsed, source-dated and revision-versioned before its offer price or quantity can become structured context. Every document hash remains in history; only the deterministic latest version is current.

Structured buyback/open-offer terms create at most one contextual forced-corporate-flow CAUSE claim per current offer. PRE terms are preferred over POST outcomes. This evidence cannot provide sponsor proof or independently unlock `CONFIRMED`; price acceptance, structure, risk, freshness and safety remain mandatory.

## D-015 Merger And Demerger Reconstruction Authority

A merger share-exchange ratio is not treated as a historical price-adjustment factor, and post-event market prices are not used to infer one because that would introduce lookahead. In-place reconstruction requires a positive explicit official factor plus confirmed predecessor/successor continuity for the same symbol. It adjusts OHLC only; volume is not rewritten.

Cross-symbol schemes require an instrument-identity lineage and a separately labeled reconstructed series. Until that exists, they remain `WAIT_DETAILS` and block price-derived scoring. Conflicting explicit factors are `CONFLICT`; no score can override either state.

## D-016 Safety Authority And Confidence Sizing

The server-side safety ledger, not browser state, is authoritative. Manual panic, daily hard loss and loss-streak locks force a no-action state and override scanner results. Recovery requires elapsed cooldown plus all five checklist acknowledgements; it resolves but never deletes prior events.

The former confidence-sizing and quantity behavior is superseded for the current research-only plan. Risk, correlation, MCX-count, liquidity, margin, lot and stress checks may produce warnings, WAIT or REJECT reasons, but cannot produce executable quantity or position intent. Averaging down remains disabled.

## D-017 Instrument And Context Date Authority

The official NSE equity master contains historical listing dates but no report date. Those row dates must never become artifact freshness. TrendForge uses the archived response `Last-Modified` timestamp for the file date and preserves parser corrections without deleting the original artifact or parse record.

Instrument identity and Nifty 500 industry membership are eligibility/context inputs only. Market regime requires separately dated Nifty history, India VIX and breadth. Missing context is `WAIT_DATA_WEAK`; VIX shock, extreme VIX or breadth worse than 1:3 is `NO_TRADE`; sector RRG direction conflict is a mandatory gate.

## D-018 Official EOD Market Context Bootstrap

The official daily CM UDiFF bhavcopy is the breadth and cash-flow authority. The official `ind_close_all_DDMMYYYY.csv` archive is the Nifty 50, India VIX and sector-index authority. The dynamic historical JSON endpoint returned HTTP 503 during live verification and is not a dependency.

TrendForge archives and parses each daily file independently. Market context requires 200 Nifty rows, current and prior VIX rows, and same-date EQ breadth. Sector context requires 60 date-aligned benchmark/sector observations. Missing history never falls back silently to yfinance.

EOD freshness is session-aware. Before the 18:00 IST publication cutoff on an open day, the expected source is the prior NSE session. After the cutoff, the current session is required. Weekends and published holidays resolve to the preceding official session. Missing calendar coverage blocks context instead of assuming weekday trading.

## D-019 Demo, License And Source-Health Boundary

Normal runtime never falls back to static radar candidates or static source
health. Demonstration records are available only when
`TRENDFORGE_DEMO_MODE=1`, remain non-executable and are labeled as examples.

The installed `pyharmonics` package contains a restrictive packaged license
despite its package classifier, and `nsepython` is GPL-3.0. Neither is a core
dependency. Their adapters are disabled unless an explicit environment flag is
set; the internal deterministic harmonic validator and official source
contracts remain authoritative.

Source health is operational evidence, not a URL-reachability badge. Every
normal-mode row exposes the last attempt, last successful content fetch,
consecutive failure count, stale threshold and known limitation. Broken or
stale structured inputs continue to block the affected gate.

## D-020 Artifact Integrity Before Parsing

Raw bytes are archived by content hash before normalization, including bad
artifacts needed for incident analysis. A shared integrity gate validates byte
length, optional externally supplied manifest hash, expected file type and ZIP
container/member safety before any source-specific parser runs. ZIP validation
includes unsafe paths, encryption, count, expanded size, compression ratio,
CRC and per-member SHA-256.

No exchange manifest is assumed to exist. TrendForge compares an expected hash
only when one is supplied by a genuine external manifest. Universal file-size
thresholds are rejected because valid official empty/small reports exist;
source-specific schema and valid-empty rules remain authoritative after the
transport/container gate.

## D-021 Ban Evidence, Derivative Schema And Resolver Authority

The official NSE `fo_secban.csv` is authoritative for the named trade date but
contains ban membership, not MWPL percentages. TrendForge stores it with
`FNO_BAN_ONLY` coverage. A matching symbol is a hard derivative veto; an absent
symbol is not proof that its MWPL percentage is safe. G13 therefore remains
`WAIT_MWPL_PERCENTAGES` until a separately verified percentage artifact exists.

F&O UDiFF requires symbol, close, previous close, open interest and OI change.
Missing fields are `WAIT_SCHEMA_MISMATCH`; numeric defaults cannot manufacture
OI evidence. Guessed dated URLs that returned 404 or HTML were removed from the
resolver. A source receives a direct resolver only after its artifact contract
has been live captured and fixture-tested.

CFTC data-date freshness follows publication availability rather than a simple
age window. Through Friday the prior Tuesday remains the latest expected public
report; from Saturday the current Tuesday is required. CFTC remains delayed
commodity regime context and cannot independently unlock MCX CONFIRMED.

## D-022 OpenAlgo Read-Only Boundary

OpenAlgo integration begins with documented market-data endpoints only:
`POST /api/v1/history` and `POST /api/v1/optionchain`. The client defaults to a
loopback URL, reads credentials only from environment variables, validates
request and response schemas, limits response size and exposes no order route.
Remote URLs require an explicit opt-in. Live gates remain disabled until user
configuration and broker-connected runtime verification are complete.

## D-023 Signed TrendForge To Trade Vision Evidence Boundary

TrendForge sends evidence, not orders. The packet contains the complete latest
scanner run, every candidate state, gate decisions, source lineage, freshness
context and command-bar safety state. A canonical SHA-256 and HMAC signature
bind the payload. Trade Vision rejects missing, tampered, future-dated,
remote-by-default or execution-enabled packets.

Rejected and WAIT candidates are retained for audit and future ML outcomes but
cannot enter an OpenAlgo handoff. A future execution phase must live outside
TrendForge, require a confirmed candidate with deterministic entry, stop,
target and position size, re-check freshness and risk immediately before
submission, and begin in OpenAlgo Analyzer/paper mode. This decision does not
authorize live order placement.

## D-024 Internal NumPy/Pandas Indicator Engine And Feature Registry Pin

TrendForge uses one deterministic internal indicator identity per selection
run: `trendforge.numpy-pandas` version `1.0.0`, currently observed with NumPy
`2.4.3` and pandas `2.3.3`. DAT-010 is the exact 39-row `FTR-001..FTR-039`
registry using File A's 22 mandatory fields. No new TA-Lib, pandas-ta or wrapper
dependency is introduced for this contract milestone.

Every `EvidenceClaim` and `SelectionScanRun` must bind to a registered feature
version, evidence family, correlation group and engine manifest. Registry lint
checks real declared read-only routes. Complete, unique, chronological closed
bars and registry-defined warm-up are required; mixed/missing engines, runtime
package drift, invalid/non-finite vectors and parity divergence fail closed.

The manifest and lint APIs are read-only. Registry presence, a backend module,
parser invocation or HTTP success does not establish live source usability,
production activation or permission to produce `CONFIRMED`. Engine/package
upgrades require a versioned contract update and reviewed parity fixtures. The
current imported-module mypy baseline is not clean and remains a documented
engineering residual rather than a reason to weaken runtime gates.

### D-030 narrow VRP research-proposal amendment

A later explicit user rule permits a non-executable VRP research proposal after
File A section 25.23 gates pass. The hidden inspector may display a
defined-risk position family, research-only lot count and hedge structure based
on user-entered scenario risk assumptions. Missing inputs return
`NO_RESEARCH_PROPOSAL`. This does not authorize a broker quantity, account
access, order intent, public-state change or execution, and it does not relax
the rejection of automatic `IV > RV` or sign-only VRP commands.

## D-033 Saved-data post-commit bridge and two-track Source Operations - 2026-08-15

The existing A1-C1 cash path is attached to the collector post-commit event, not rebuilt and not invoked by the browser. A source must first produce a schema-valid parsed artifact committed as current last-good data with content hash and session/date identity. Only then may the bridge dispatch A1, A2, A3, A4, A5, A6, C0, conditional B and C1.

The bridge is idempotent by relevant content fingerprint, ignores unrelated source changes, preserves collector success when research processing fails, and records FAILED_STAGE for downstream errors. C0 is a permission read/rebuild boundary, not a per-download compiler rebuild. MWPL remains missing until a real official percentage artifact is proven.

Source Operations is a read-only projection at GET /api/source-operations/snapshot. It has two tracks: source flow from compiler, attempt, parser, freshness and last-good evidence; and cash A1-C1 post-commit status. It does not expose catalog samples as evidence, activate sources, authorize CONFIRMED, calculate quantity or execute orders. Inventory topology counts remain catalog-derived and are not hardcoded into the backend.

This decision is verified by focused tests, but a live end-to-end refresh remains unclaimed until the running server is restarted and a real cash last-good artifact completes the bridge.

## D-034 R1/R2 remaining work is not the workbench page - 2026-08-16

Cash A1â€“C1 is the implemented research spine. Remaining File A **R1** is the live evidence DTO (alias-aware last-good, cadence clocks, `missing_evidence` / `why_not_confirmed`, PIT bundle). Remaining File A **R2** is attention order over those states plus an inventory A-score **shadow** queue. R2 does not rebuild S0â€“S3. R2-B activation stays closed.

The Inventory Workbench / Source Operations integration page is collector and cash-stage **glass only**. It is not connected to R1 live stock evidence or R2 ranking. Catalog samples, last-good counts, and Consensus/Screener in the drawer are not File A evidence or rank. A later, separately approved display ticket may bind the DTO to a page. Until then the honest sentence is: collector health is visible; live stock evidence is not on this page; attention ranking is not on this page.

## D-035 R3â€“R15 stay off the workbench and off fixture radar - 2026-08-16

R3â€“R15 were debugged against the post-collector / post-workbench plan before any new wiring. `resolve_evidence`, `analyze_closed_bar_structure`, `evaluate_option_chain` and `evaluate_mcx_contract` remain fixture-ceiling functions. Cash post-commit does not call them. `/api/radar` and `build_live_selection_run` are a third path. The workbench is a fourth path.

Future live R3 must consume the R1 DTO via locked plan **Â§13** only. R3 does not write `public_state`. R5 live CONFIRMED stays closed until File A R2-B activation plus official CA join (R14). R15 is the TrendForge Scanner Lab, not `/inventory-workbench`. Q5 fixture CONFIRMED must not appear as live. Do not re-open an R3 design debate at build time.

### D-035 amendment - R3 exact-lineage and authority prerequisite (2026-08-16)

R3 must follow locked plan section 13 including binding correction 13.9. The live adapter consumes exact A1 SourceResult and A2 NormalizedFact objects plus compiled source contracts; public R1 display DTOs, inventory cards and records_sample cannot create claims. Selected claims are prohibited while compiler feature IDs/directional permission are absent. R3 owns only resolution WAIT/block diagnostics and cannot mutate R2 state/order. A separately approved canonical source-contract amendment is required before meaningful selected claims.
### D-035 implementation amendment - R3 is live but WAIT-only (2026-08-16)

The separately approved canonical prerequisite is implemented as FTR-040. It is deliberately narrow: one closed NSE EOD cash fact can create at most one `PARTICIPATION` claim for SWING/NSE_EQ under `RESEARCH_DIRECTIONAL_WAIT_ONLY`. The adapter consumes exact A1/A2 lineage and current R1/R2/compiler hashes. R3 does not rewrite R2, activate sources, infer independent confirmation, or emit trade geometry. Intraday, MCX, options and event evidence remain unavailable to live R3 until their own reviewed source-feature contracts are implemented in later milestones.

### D-036 live R4 is ID pin + PK inventory, not A2/A4/R5 - 2026-08-19

File A R4 live (`selection/r4_live.py`, `GET /api/v1/selection/identity-pin`) binds R2 rows to existing A2 instrument IDs, refuses companion scrip codes, and persists the pinned PK inventory digest. It is not canonical identity (A2), not PIT bars/CA vintages (A4), not Q5-R4 enrichment fixtures (`r4_fixtures.py`), and not the R7 PK worker. PK `upstreamCanVote` and `runtimeRequired` stay false. R4 cannot rewrite R2/R3/R5 or emit CONFIRMED. Early delisting uses explicit PIT fixtures only; otherwise `PIT_UNPROVEN`. Gemini/other agents must not treat A2/A4/R5 as R4.

### D-039 live R14 is the CA join R5 must consume; WAIT-only - 2026-08-21

File A R14 live (`selection/r14_live.py`, `GET /api/v1/selection/ca-join`) joins already-collected official corporate-action observations (`nse_corporate_filings_actions`, job `CA_SOURCE`) onto R2 rows through the R4 A2 `instrument_id` pin. It reuses `corporate_actions.reconcile_corporate_actions` for DAT-022 factor semantics and never rewrites those formulas; `ALGORITHM_VERSION=DAT-022-v1` is pinned and any factor change must bump it. The join is hash-scoped to current R1/R2/R4 (mismatch â†’ `WAIT_R14_*` / 503, never silent last-good), replay at `decision_at` cannot see a CA with `available_at > decision_at`, and cross-symbol predecessor/successor without same-instrument proof is `IDENTITY_BREAK`, never a ticker follow. R5 must consume the R14 row as its only CA authority: `WAIT_CA` rows drop structure `claim_ids`, volume divides only for SPLIT/BONUS, and RAW bars never mutate (adjusted series via `series_layers.open_adjusted_series`, keyed by `factor_version`). R14 is not A2, not A4 vintage storage, not a 124th voter, not R6 sponsor votes, and cannot confirm, rank, or size. Confirmed/partial conflicts stay WAIT; live CONFIRMED still requires R2-B plus a separate File A amendment.

New files: `backend/trendforge_api/selection/r14_live.py`, `backend/tests/test_r14_live_ca_join.py`. Wired into: `backend/trendforge_api/selection/cash_post_commit.py` (stage R4 â†’ R14 â†’ R5, `PIPELINE_VERSION ...orchestrator-7`), `backend/trendforge_api/selection/r5_live.py` (consume + `r14RunId`/`r14RunHash`), `backend/trendforge_api/main.py` (GET routes), `backend/trendforge_api/market_data_scheduler.py` (backfill refresh rebuilds R14 first).

### D-038 Hybrid S4/S5 paper A/B stays until user picks - 2026-08-21

Original v3 compressed S4/S5 (B4/B5 mixed into `pÌ‚`, wall used as entry) and the split family (`pÌ‚` from B1â€“B3 proxy; B4 package; B5 location) both remain as a research overlay. The user will choose after future paper days. `GET /api/v1/selection/s4s5-compare` and `#s4s5ComparePanel` checkboxes WITH / WITHOUT / BOTH display both results. Numbers are `RESEARCH_PROXY_NOT_CALIBRATED`. This is not a File A milestone, not live `pÌ‚`, not size, and not CONFIRMED. Do not delete either formula family and do not paste them into `r5_live.py` until that pick plus R14 + R2-B.

New files: `backend/trendforge_api/selection/s4s5_compare.py`, `backend/tests/test_s4s5_compare.py`, `frontend/s4s5-compare.js`. Wired into: `backend/trendforge_api/main.py`, `frontend/index.html`, `frontend/styles.css`, `frontend/tests/acceptance-check.js`.

### D-035 implementation amendment - R5 is live but WAIT-only (2026-08-19)

Live R5 (`selection/r5_live.py`, `GET /api/v1/selection/structure`) is closed-bar research over official NSE cash last-good plus official index-close context. Detected setups are tags on WAIT rows. The live batch cannot persist CONFIRMED, cannot set `canUnlockConfirmed`, and cannot treat UTC wall-clock as the NSE session. Phase and research date use Asia/Kolkata: open session researches the previous trading day; EOD window after 15:35 IST may promote today only after the dated official file parses as today; holidays keep the last trading day and do not relabel it as calendar today. R14 CA join is live WAIT-only and is R5's CA authority (D-039). R2-B activation remains closed, so File A â€œfirst honest CONFIRMEDâ€ is not this milestone.

## D-037 Plan-file provenance audit, salvage, and archive - 2026-08-19

Completed formal provenance audit of 13 historical, review, and candidate plan files against File A (`docs/fable/new_merge_PLAN_2026-07-18.md`), File B (`docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md`), Final Merge (`docs/fable/FINAL_MERGE_PLAN.md`), and live R0â€“R5 code ceilings.

1. **Authority hierarchy reaffirmed:** File A is the sole build-sequence authority. File B is domain detail only when pointed to by File A Â§0.5/Â§25. Live R0â€“R5 ceilings, 123-job registry count, 4 public states (`WATCH`/`WAIT`/`CONFIRMED`/`REJECT`), and research-only non-execution posture remain invariant.
2. **Archived superseded files:** Historical plans (`HYBRID_MASTER_PLAN.md`, `TRENDFORGE_STOCK_SCREENER_MERGE_PLAN_2026-07-18.md`, `STOCK_SCREENER_PLAN_FLOW_REVIEW.md`), external drafts (`TRENDFORGE_HYBRID_V2.md`, `TRENDFORGE_HYBRID_V3.md`), and completed scoped campaign packets (`ADD_40_SCREENER_LINKS_PLAN.md`, `FII_STOCK_SIGNALS_PLAN.md`, `FREE_SOURCE_RECOVERY_77_PLAN.md`, `FRONTEND_SHELL_ALIGNMENT_PLAN.md`, `LIVE_PANELS_PLAN_2026-08-04.md`) are archived under `delete/plans_archived_2026-08-19/`.
3. **Evidence retained:** `INDEPENDENT_AUDIT_hybrid_vs_new_merge_2026-07-20.md` and `INDEPENDENT_AUDIT_merge_plan_build_matrix_2026-07-20.md` remain in `docs/fable/remaining_build/` as active dual-file audit evidence.
4. **Research overlay salvage:** Hybrid V3 Upgrades 28â€“33 (physical settlement margin ramp, publication-lag timestamps, 5-min bar recorder, participation cap, macro calendar, option mid \(\pm\) half-spread fills) are salvaged into `docs/OPTIONS_INTELLIGENCE_PLAN.md` Â§18.12 as non-live research overlays.

### D-042 R0-B prove-five + MWPL wait; activation draft not executed - 2026-08-22

R0-B now proves shared NSE domain fetch policy (rate cap, HTTP retry max 3, `DomainCircuitBreaker` fail=3/cooldown=900s, 5-day hash retention) as compiled **fields**, not fake per-source unique breakers. Confirm-path members (`nse_bhavcopy_eod`, `nse_fno_ban`, `nse_fo_bhavcopy`, `nse_index_close_eod`, `nse_corporate_filings_actions`) can be `proven=true` and `confirmEligible=true`. `nse_mwpl_percentages` stays unproven and **not** confirm-eligible: there is still no verified official percentage artifact; the ban CSV cannot satisfy MWPL %. `canVote` and `sourceActivationReady` stay false. Named activation list is drafted in `docs/fable/remaining_build/FILE_A_R2B_ACTIVATION_AMENDMENT_DRAFT.md` and is **not** executed. Qty/broker stay closed.

### D-041 live R2-B is a named activation ledger, not the confirm unlock - 2026-08-22

File A R2-B live (`selection/r2b_live.py`, `GET /api/v1/selection/named-activation`) **names** the R0-B official cohort sources and records that none of them may support CONFIRMED. Ceiling `LIVE_NAMED_ACTIVATION_WAIT_ONLY`. Validators forbid `sourceActivationReady=true`, `canUnlockConfirmed=true`, `authorizedCount!=0`, and `maySupportConfirmed=true`. This is the same pattern as R4 (pin without PK vote) and R14 (join without CONFIRMED). It does **not** meet File A Â§9.6.1 / Â§25.20.1 for flipping compiler activation. R0-B `provenCount` stays non-voting; `gateAuthorized` stays 0. Live CONFIRMED still needs a separate File A amendment.

New files: `backend/trendforge_api/selection/r2b_live.py`, `backend/tests/test_r2b_live_named_activation.py`, `frontend/r2b-activation.js`. Wired: `backend/trendforge_api/main.py`, `frontend/index.html` `#r2bActivationPanel`.

## D-040 Hybrid V2 paper overlay != R2-B != CONFIRMED - 2026-08-22

The Hybrid V2/V3 trading-OS overlay ships as a read-only research package in
ackend/trendforge_api/hybrid_v2/. It consumes the live File A spine
(R1, R2-A, R4, R14, R5) hash-matched or fails closed with 503. The adopted
S4/S5 split wins over V2 Part E: WITHOUT p-hat uses B1-B3 proxy only, B4 is a
package that never changes p-hat, B5 is location-only labels, geometry never
votes. Overlay rows can never be CONFIRMED, never set qty, never activate a
source, and never write into R2/R5/R14 (test C14 locks the hashes). AS
delivery is the only real block and only from official nse_mto_delivery
last-good; volume is never a delivery proxy; WAIT_CA hides the delivery z.

## D-044 Evidence radar uses all jobs as typed slots - 2026-08-22

The 3rd-eye evidence radar (selection/evidence_radar/) reads every live R1
source contract as exactly one typed slot (PRESENT / VALID_EMPTY / STALE /
WRONG_GRAIN / BLOCKED / UNPROVEN / NOT_NORMALIZED / COMPANION_ONLY /
NOT_APPLICABLE). 123 jobs are never 123 votes; aliases share a dataset root;
the index-close companion is not a 124th job. Four horizon boards
(INTRADAY / SWING / POSITION / COMMODITY) are WAIT-only research displays with
how/what/where/when plus File A's eight radar questions. Delivery is forbidden
on the intraday horizon; AMFI/SHP stay delayed; 
se_fii_dii remains a
market-level chip; commodity seats require local MCX context, never CFTC/WGC
alone. 0 CONFIRMED, qty=0, sourceActivationReady stays false.
### D-044a Calculate-layer fill (same day) - recipes wired, facts never invented

RS now uses Nifty 50 closes as benchmark; R5 setup tags join STRUCTURE under
the same correlation group as gap (no second structure vote); delivery z is a
20-session robust PIT recipe that stays UNKNOWN until an MTO last-good exists;
pre-open IEP gap feeds INTRADAY discovery only, never an ORB confirmation;
most-active joins the single R2 session story. Every remaining UNKNOWN is
file-missing, not formula-missing.


## D-045 S2 market weather is context - 2026-08-22

The Nifty percent bug is fixed at parse time: bare CHANGE/variation columns
are points and never enter a percent field; official percent keys win; missing
percent recomputes from previous close or points, else fails closed to null +
INDEX_PCT_PARSE_REJECTED (never a pretty zero). S2 emits one WAIT-only DTO
(index/VIX band/breadth-or-UNKNOWN/official sector ranks/local-MCX-vs-grey-
global) with regime labels RISK_ON|RISK_OFF|MIXED|RANGE|UNKNOWN that are
research weather only. Index is a companion: it cannot confirm a stock, add a
second vote to R2, or seat commodity boards without local MCX bars.

## D-046 S3 preserves R2 order while scanning the full eligible universe - 2026-08-24

S3 is an additive cheap-discovery pass, not a third ranker. It consumes the
current A3/R2 lineage, scans every current R2 row, and preserves `attentionRank`.
Pre-open, most-active, OI, event-index, EOD RVOL, NR7 and benchmark-relative
strength are typed observations from last-good source snapshots and PIT bars;
missing optional inputs remain UNKNOWN rather than becoming zero or failure.

One A4 symbol-set query and one cached NIFTY benchmark replace per-stock history
queries. Completeness is explicit across eligible, scanned, excluded, failed and
unattempted rows; any partial scan caps research rows at WAIT. S3 does not query
delivery, add a second volume vote, infer deal/FII direction from event presence,
change R2 rank, emit entry/target/stop/quantity, activate sources or produce
CONFIRMED. The public surface is two read-only GET routes and compact WATCH
queues in All Stocks and Live Ops.

## D-047 S4 = SEL-005 on live R5; not Hybrid S4 p-hat; not CONFIRMED - 2026-08-24

The S4 structure pack (selection/s4_structure_pack.py) extends the persisted
hash-matched R5 batch into a WAIT display pack. Breakout acceptance and trend
acceptance share ONE CG_PRICE_STRUCTURE representative claim id per row; NR
compression stays max WATCH; the pattern lane is display-only and can never
support CONFIRMED. Hybrid V2/V3 S4 p-hat, Kelly and B1-B5 stay in the hybrid
overlay and never enter R5/S4. Trigger/invalidation labels are research text,
not trade geometry.

## D-048 S5 = SEL-006 shortlist only; Options Detail Plan package not R12 complete - 2026-08-24

S5 enrichment runs only on the S4 structure-claimed shortlist (fallback: R2
WATCH intersect latest R5 setups). Delivery is EOD-only with an INTRADAY
forbidden guard; one FO OI package per A6; OPTIONS_PACKAGE stays
UNKNOWN_NEEDS_R12 until a fresh expiry-scoped chain contract is proven, with
score 0 so cash-only names are never punished; unnamed deals are never FII;
nse_fii_dii stays a market chip; shpFiiDelta remains null. S5 does not mark R12
done and does not emit CONFIRMED.

## D-049 S6 = SEL-007 FUS-009 over S4+S5 claims; R3 stays diagnostic; not Combined_Score; not CONFIRMED - 2026-08-24

S6 family resolution resolves lineage-backed claims through the canonical
resolver with the ACTIVE VERSIONED PROFILE OBJECT supplying required families
(no hardcoded STRUCTURE+PARTICIPATION constant, epsilon stays 0 without a
versioned profile saying otherwise). Evidence strength is labelled exactly
"Evidence strength - not win probability". Conflict blocks any BUY/SELL seat.
S5 enrichment fields remain context notes, not votes. S7 profile gates and the
R2-B unlock amendment own any future CONFIRMED.

## D-050 One family-resolution board: /s6-resolution; thin R3 /resolution stays diagnostic - 2026-08-24

The S6 board (GET /api/v1/selection/s6-resolution) is the single
family-resolution surface: it ingests merged_feed (cash FTR-040 participation
unioned with R5 structure claims, one representative per correlation group) and
bounds its rows to the S4/S5 structure-claimed shortlist. The old
GET /api/v1/selection/resolution stays the persisted hash-matched R3
diagnostic per D-049; it is not deprecated until consumers move. Cash-feed
assembly failures degrade the board to structure-only with explicit warnings;
they never block or 503 the board.

## D-051 S8 = one reconstructable scan blob; store helpers added - 2026-08-25

`selection/s8_persist_run.py` assembles ONE immutable blob per scan run:
lineage ids for R1/R2/R14/R5/S2/S3/S4-pack/S5/S6/S7 (absent stages named
`WAIT_STAGE_ABSENT`, never invented), S2 weather block with suspect flags,
S3 completeness tuple, rows copied verbatim from S7 idea cards (publicState
never re-scored), changeKinds vs prior comparable run, STO-008 state events
into existing `selection_state_events` table (WAIT sentinel for first-ever
baseline). Ceiling `LIVE_S8_RECONSTRUCTABLE_WAIT_ONLY`.

Store helpers added: `get_selection_payload(profile_id, run_id)` and
`list_latest_selection_payloads(profile_id, limit)` — same tables, no new
database. Store duplicate-run_id behavior changed from `sqlite3.IntegrityError`
to `ValueError` for clarity (all existing callers keyword-based, none catch
IntegrityError). Known limitation: payload + state-events commit on two
connections (non-atomic; deferred to R16 migration approval).

## D-052 Research quantity at draft-confirmed eligibility - 2026-08-25

User-requested research position sizing at the confirmation point. NOT File A
product `final_qty`; NOT OMS; NOT a broker order. `researchQuantity` is a
label on WAIT rows where `draftConfirmedEligible=true`. Formula uses
researchCapitalInr × researchRiskPct ÷ unit_risk × data_quality_cap ×
regime_cap × liquidity_cap × calibrationCap. All caps in 0..1. Evidence
strength never increases qty. See dual-lane prompt for full contract.

## D-053 R2-B activation amendment: observed five-source flip + guidance OMS - 2026-08-25

Ticket 4/4 executed the File A R2-B draft. Decision: the named-activation
ledger itself is the activation authority; it authorizes exactly the five
confirm-path sources when each has an OBSERVED current official last-good
(snapshot present, latest snapshot parsed PARSED_STRUCTURED, non-empty or
valid-empty, data_date inside registry freshness window evaluated at the
bundle trading_date). All-or-nothing global flip: one missing last-good keeps
sourceActivationReady=false (fail-closed execute is a success outcome).
Compiler gatePermission stays untouched (OPN-003: OpenAlgo/compiler labels
never become confirm authority). S7 seats publicState=CONFIRMED for PRF-003
EOD rows only after the full checklist, under batch-level
sourceActivationReady=true; CONFIRMED-without-ready remains a hard validator
error (kept regression). Guidance OMS is a separate module so S7 stays free of
order paths; live placement requires env TRENDFORGE_LIVE_ORDERS=1 AND lane
OPENALGO_RO AND UI arm switch, default OFF, 409 LIVE_ORDERS_ARMED_OFF.
Intraday gets guidance confirmation only (intradayGuidanceConfirmed), never
public intraday CONFIRMED - no intraday source is named in this amendment.

## D-054 R8 native core scanner registry - 2026-08-25

Five versioned native cores (breakout, trend, NR compression, RVOL, volume
thrust) WRAP the existing R5 closed-bar engine by citing its FTR-006/007/017
claim ids; no third structure engine exists. parameterHash = SHA256 of sorted
compact JSON parameters (STO-016). pkCompatible is a parity-fixture marker
only where PK_R4_NATIVE_MAP covers the feature (FTR-005/006/007); it never
grants a vote. Twin scanners sharing one claim (breakout+trend on
CG_PRICE_STRUCTURE; rvol+thrust on CG_ACTIVITY_SESSION) fold into ONE
representative per group (FUS-009 first-wins in registry order) and are
labelled correlated_possible, never independent confirms. Universe = full
hash-matched R5 rows (documented; one A4 set-query already performed by R5).
Run identity hashes definition hashes + r5/r14 run hashes + rows; lineage
mismatch surfaces as typed 503 via the shared spine gate. S3 may attach
nativeCoreMatches as batch-level cheap facts with rows byte-identical (rank
cannot change). S6 ingest (merge_native_claims) fills EMPTY correlation groups
only, first-wins per group, never overrides R5 claims; production routes do
not inject this ticket. confirmedCount pinned 0; executable false; PK shadow
failure degrades to a warning only. POST /scanners/run is 405 (compute-on-GET
like S4; no dual-start collector). No place_order anywhere under scanners/.

## D-055 R9 skipped; R10 pipe DSL built under FUS-010 - 2026-08-26

Operator decision 2026-08-25/26: **R9 (ORB/VWAP) is skipped**, not dropped -
it stays CSV PARTIAL and returns only when verified intraday bars exist
(OPENALGO_RO lane or a free NRT source). No R9 code was written.

R10 implemented as File A PK5: scanners/pipe_dsl.py is the LIVE module for
the FUS-010 pipe DSL. Name mapping: File A's pk_pipe_dsl.py stays RESERVED
for the PK shadow harness; PK may import this module later. Grammar v1 =
UNION / INTERSECTION / FILTER_STATE / ENRICH_S7 over R8 native-core match
sets; first stage must be a scanner stage; unknown op/scanner fails the whole
run typed (PIPE_INVALID_STAGE); ENRICH never filters; FILTER_STATE without
an S7 board fails closed (WAIT_R10_S7_NOT_READY). Stage counts are symbol
counts so correlated twins cannot inflate membership. Pipes emit ZERO claims:
no EvidenceClaim construction, no claim ids on output DTOs (validator pins
confirmedCount=0). Two seeded recipes (breakout_watch, thrust_participation),
STO-016 parameterHash over sorted stage JSON, run identity = def hash +
native-core run hash + s7 run hash + stages. Compute-on-GET only;
POST /api/v1/pipes/run is 405; nothing persisted.

## D-056 MCX WAIT without official master; cash path untouched - 2026-08-25

R11 delivers an honest readiness board (selection/r11_mcx_live.py, schema
trendforge.mcx-master.v1, ceiling LIVE_MCX_WAIT_WITHOUT_NAMED_ACTIVATION):
MCX leaves WAIT only with a structured official master last-good AND current
local mcx_bhavcopy bars; missing lot/tick/expiry seat WAIT with named codes
(never invented); a tender-window hit vetoes READY. FBIL USD/INR, CFTC and
WGC are delayed context - none can unlock MCX intraday or confirm anything.
PRF-005/006/007 boards stay EMPTY (mcx_profile_blocker returns
WAIT_MCX_MASTER); R2-B named activation is NSE-five-only so the whole MCX
branch keeps canUnlockConfirmed=false and executable=false. Swing RS/delivery
reuse S3/S5 evidence as gates only (swing_rs_gate / swing_delivery_gate);
delivery stays EOD-only exactly as S5 enforces (FORBIDDEN_ON_INTRADAY).
Cash S7 spine unchanged: full suite regression green after the build.
## D-057 Scanner Lab lives in the inspector; no radar inflation - 2026-08-25

R15 delivered as a UI + one-fetch BFF: GET /api/v1/scanners/lab-bundle returns
ONE 200 whose inner entries carry named codes on an unhealthy spine (never a
second collector; POST forbidden). Lab mounts inside #q5Inspector as its own
tab (registered by frontend/scanner-lab.js via MutationObserver so payload-
driven q5 tabs can wipe it) with sub-tabs Definitions / Pipe flow / Symbol /
PK shadow. All Stocks columns are frozen: acceptance-check pins the exact
radar <th> template and forbids <th> in the new lab owners. #scannerRunButton
is relabelled "Refresh lab (GET)" and only re-fetches the bundle - the legacy
runScannerOnce fire is disconnected. PK shadow parity renders descriptive
chips (PK_SHADOW / PARITY_UNKNOWN until the harness is wired) and cannot
change S7. S9 guidanceWinRate appears only as an on-demand per-symbol
footnote inside the lab; All Stocks keeps no second scoreboard.
## D-058 R13 family batches as CHIPS-ONLY scanners - 2026-08-26

Six bounded-family scanners (VCP, TTM squeeze, SMA20/50 trend overlay,
Wilder RSI14 momentum, symmetric failed-break reversal, 10d/52w PIT extremes)
remain ZERO-EvidenceClaim guidance chips. R13 reads one bulk set of hash-matched
R5/R14 adjusted closed EOD bars and fails closed when identity, adjustment or
lineage is missing. Claim evidence still uses `representative_matches`;
claimless display guidance uses `representative_guidance_chips`, one visible
representative per family/group with suppressed siblings retained in Scanner
Lab. RSI is the shared pure-Python Wilder implementation in
`native_extended.py`; TTM uses EMA20 and Wilder ATR10 true range, not a close
range proxy. Additive guidance fields cannot change candidate direction, rank,
S7 public state or confirmation. No ORB/VWAP modules or ids (R9 stays skipped).
## D-059 R16 uses normalized exact-cell PIT storage and backend authority - 2026-08-28

R16 adopts six normalized tables in the existing SQLite database, not the
legacy 20-row PIT gate, one generic JSON payload or a second database. Shared
S8Service is the sole S8 construction owner; immutable R16 hypotheses remain
separate from S8 null geometry. Later observations, folds, metrics and approval
transitions are append-only and revision-bound. CLI/EOD owns writes; GET routes
and the frontend are read-only projections.

Implementation verification and PIT approval are different claims. Until the
live 0013 migration, populated replay and acceptance checks pass, runtime stays
BUILDING / PIT_NOT_APPROVED. Even a later PIT_APPROVED exact cell cannot grant
CONFIRMED, prediction probability, model promotion, broker access, orders or
executable quantity. R16 v1 is NSE cash EOD swing only; intraday, options and
MCX require separate approved contracts.


## D-060 R16 migration is active but PIT approval remains data-gated - 2026-08-29

After an integrity-checked online backup, migration
`0013_r16_pit_substrate` was applied to the existing TrendForge SQLite database.
No second database or legacy client-side approval calculator was introduced.
The normalized store, append-only replay, worker lease/checkpoint, indexed
read-only queries and compatibility projections are the accepted R16 v1
implementation.

Implementation completion does not waive evidence floors. The first real
complete S8 date created one dataset and 2,034 horizon-bound observations, but
one date is insufficient for folds, holdout and calibration. The authoritative
state therefore remains `BUILDING / PIT_NOT_APPROVED`. Probability,
confirmation and execution authorization remain false. Historical incomplete
S8 artifacts stay immutable and rejected. Browser rendering is a recorded
verification caveat; it cannot be converted into approval.
# D-054 - R17 keeps research quantity and separate option-purpose votes

Date: 2026-08-31

Decision:

- retain deterministic `researchQuantity`, research risk, notional and
  hypothetical position calculations with `executable=false`;
- do not use OpenAlgo broker funds, positions or order APIs;
- expose PCR, OI-wall, max-pain, IV-regime, Greeks-convexity,
  option-liquidity and unsigned-gamma-fragility as separate versioned votes;
- retain common chain snapshot lineage and a concentration diagnostic rather
  than silently merging the votes;
- do not call vote strength, confluence or freshness a win probability.

Reason: the current user explicitly requires quantity guidance and separate
option calculations because they answer different trading questions. The
read-only and non-executable boundaries remain unchanged.

## D-061 R17-C keeps REST validation inside the existing client - 2026-08-31

OpenAlgo ping, intervals, quote, multiquote and history validation remain in
`openalgo_client.py`; OHLCV projection remains in `source_adapters.py`. A
second downloader/service was rejected because it would duplicate credentials,
retry state and ownership. The client fails closed on valid-empty history,
partial multiquotes, identity mismatch, impossible/non-finite market values and
requested freshness failure. Only transient transport failures are retried;
rate budgets and circuits are route-local. Errors must redact the API key.

This fixture-verified client does not claim exact instrument binding, replay,
stream continuity, live broker data, execution or production readiness.

## D-062 R17 shadow is additive and activation requires observed proof - 2026-08-31

`openalgo_shadow.py` is the sole R17 projection owner after R1-R16. It copies
the base public state, emits zero confirmations and remains non-executable.
Exact identity, replay and stream integrity stay in their existing R17 owner
modules. The frontend renders the backend DTO; it does not calculate state,
quantity or option votes.

The seven option-purpose views remain separately inspectable because they
answer different questions, but common root/snapshot/raw lineage is mandatory
and their independent-confirmation count is zero when they share one chain.
Research quantity includes declared per-unit costs; quantity is rounded to the
lot multiple once, and notional is quantity times entry without multiplying
the lot size again.

Configuration is not live evidence. `OPENALGO_ENABLED=1` may expose only the
fixture checkpoint; it cannot select `OPENALGO_RO` or produce `SHADOW_LIVE`.
Live stages require separately approved observed REST, replay, stream,
reconnect and provider-continuity evidence. Turning R17 off must stop stream
activity, reject network/storage work and preserve the canonical R1-R16 hash.

## D-063 R17-G is deferred and R18-A becomes the active milestone - 2026-09-01

The user chose to skip the fresh Kite login and leave R17-G for future work.
This is `POSTPONED_BY_USER`, not R17 completion and not permission to claim
`REST_SHADOW_OBSERVED`, `STREAM_SHADOW_OBSERVED` or `SHADOW_LIVE`. R17-B-F and
R17-H/I remain fixture-verified. The approved bounded attempt and `60m` client
repair remain valid evidence; OpenAlgo stays optional, read-only,
non-authoritative and non-executable. R9 ORB/VWAP stays postponed until a
verified intraday-bar source exists.

R18-A model-governance foundation is the next active File A milestone. It must
reuse R16 immutable PIT datasets and replay, keep current public states
unchanged, and begin with `MODEL_NOT_APPROVED`. Accepted scope is versioned
champion/challenger contracts, offline evaluation, human-only promotion, drift
demotion, deterministic rollback and read-only API/UI projection. Current R16
runtime is `PIT_NOT_APPROVED`; therefore probability/performance presentation,
automatic promotion, broker access, execution and executable quantity remain
locked.

