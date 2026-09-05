# R17 OpenAlgo Shadow Build Plan

Status: R17-B-F AND R17-H/I FIXTURE_VERIFIED; R17-G POSTPONED_BY_USER
Updated: 2026-09-01
Authority: explicit user instruction in the current task, then AGENTS.md and File A
Checkpoint: R17-B-F and R17-H/I FIXTURE_VERIFIED; R17-G POSTPONED_BY_USER after the 2026-09-01 blocked live attempt

## 1. Objective

Add OpenAlgo as an optional read-only market-data overlay after the existing
public-source collector and R1-R16 research pipeline.

```text
100+ public sources
  -> existing download / parser / storage
  -> R1-R16 base research and shortlist
  -> R17 exact instrument binding
  -> OpenAlgo REST / optional stream observations
  -> research quantity + separate option-purpose votes
  -> WATCH / WAIT / REJECT display
```

R17 does not replace, restart or duplicate the existing public-source collector.
It reads only the canonical shortlist and never changes the base R1-R16 state
owner.

### Design selection

Three materially different mechanisms were compared:

| Approach | Primary risk | Estimated fixture-milestone success |
|---|---|---:|
| Contract-first inside the existing client | Provider docs may still drift | 79% |
| Add client methods before pinning schemas | Silent request/response mismatch | 58% |
| Build a separate OpenAlgo shadow service | Duplicate ownership and recovery paths | 36% |

The estimates are planning ranges, not trading probabilities. For the selected
approach the rough decomposition is contract accuracy 95% x integration fit 92%
x regression survival 90% = about 79%, with a 70-88% judgment range. The weak
link is live broker-specific behavior that fixtures cannot prove. The cheapest
falsification test is the R17-B pinned contract endpoint followed by fixture
validation before any credentialed request.

## 2. Current User Decisions

### R17-QTY-DEC-001 - Keep research quantity

TrendForge shall calculate research direction, entry reference, invalidation,
targets, quantity, reserved risk, hypothetical notional and remaining research
capital. These are research guidance, not broker balances, positions, orders or
execution permission. Every DTO remains `executable=false`.

### R17-OPT-DEC-001 - Separate option-purpose votes

The options package shall not collapse every calculation into one vote. Each
calculation receives its own vote ID, purpose, formula version, freshness,
applicability, raw strength, direction and explanation.

The same snapshot/expiry lineage remains visible on every vote so a trader can
see when several votes came from the same option chain. A concentration
diagnostic is shown, but it does not silently merge the requested votes.

| Vote ID | Trading purpose | Directional use |
|---|---|---|
| `OPTION_PCR_CROWDING` | Put/call positioning imbalance | Bullish, bearish or neutral crowding |
| `OPTION_OI_WALL_STRUCTURE` | Nearest meaningful call/put OI barriers | Support, resistance and breakout room |
| `OPTION_MAX_PAIN_MAGNET` | Expiry-local settlement magnet | Low-priority pull toward max-pain near expiry |
| `OPTION_IV_REGIME` | Volatility price and percentile | Risk/regime vote; direction only with a declared setup |
| `OPTION_GREEKS_CONVEXITY` | Delta/gamma/theta sensitivity | Setup risk and convexity confirmation |
| `OPTION_VOLUME_LIQUIDITY` | Tradability and participation | Readiness/liquidity vote, not automatic direction |
| `OPTION_GAMMA_FRAGILITY` | Unsigned gamma concentration | Pin/acceleration risk; never dealer positioning |

No vote uses a missing input as zero. Non-F&O securities use
`NOT_APPLICABLE`. Partial or crossed chains use `WAIT_PARTIAL_CHAIN`.
The first implementation exposes raw separate votes; production weights remain
versioned and provisional until point-in-time calibration.

## 3. Hard Boundaries

- OpenAlgo is disabled by default.
- Missing credentials do not stop TrendForge.
- R17 never promotes a base state and never produces `CONFIRMED`.
- An outage can hold an OpenAlgo-dependent profile at `WAIT`; it does not
  independently invalidate the stock.
- No OpenAlgo account, funds, holdings, positions, margin or order method is
  added by R17.
- Research quantity may be non-zero but remains `executable=false`.
- Evidence strength, freshness and option confluence are not win probability.
- No dependency install, database migration, credentials or live stream without
  separate approval.

## 4. Provider Contract

Pinned local OpenAlgo commit:

```text
24f8d395372799066a24ba1d6311f0e7791555d8
```

TrendForge owns an exact allowlist. OpenAlgo may contain trading APIs, but
TrendForge must not construct or call them.

| Route | Method | R17 purpose | Initial state |
|---|---|---|---|
| `/api/v1/ping` | POST | Local service readiness | CLIENT_IMPLEMENTED |
| `/api/v1/intervals` | POST | Broker-supported candle intervals | CLIENT_IMPLEMENTED |
| `/api/v1/quotes` | POST | One-symbol snapshot | CLIENT_IMPLEMENTED |
| `/api/v1/multiquotes` | POST | Shortlist snapshot | CLIENT_IMPLEMENTED |
| `/api/v1/history` | POST | Closed candles | CLIENT_IMPLEMENTED |
| `/api/v1/optionchain` | POST | Expiry-scoped chain | CLIENT_IMPLEMENTED |
| `/api/v1/optiongreeks` | POST | One-contract Greeks | CLIENT_IMPLEMENTED |
| `/api/v1/multioptiongreeks` | POST | Batch Greeks | CLIENT_IMPLEMENTED |

Provider documentation and implementation disagree on WebSocket fields:
`instruments/quote/type=quote` versus
`symbols/Quote/type=market_data`. Both are recorded as protocol variants;
neither is selected until observed against the installed server.

The provider currently exposes no verifiable market-event sequence number.
TrendForge may add a local receipt sequence for deterministic ingestion but
must label provider continuity `STREAM_SEQUENCE_UNAVAILABLE`.

## 5. Data Contracts

### 5.1 Capability

Public capability states remain `ABSENT`, `DISABLED`, `FIXTURE_VERIFIED`,
`SHADOW_LIVE` and `REJECTED`. `SHADOW_LIVE` requires observed REST/stream
behavior, replay integrity and all applicable File A stream tests.
Configuration alone never proves it.

### 5.2 REST quality

Use `VALID_POPULATED`, `PARTIAL`, `STALE`, `FETCH_FAILED`,
`SCHEMA_CHANGED`, `IDENTITY_FAILED`, `CONFLICT` and contract-specific
`VALID_EMPTY`. A targeted quote cannot be `VALID_EMPTY`. Every requested
multiquote member must reconcile; missing members produce `PARTIAL`.

### 5.3 Snapshot envelope

Every accepted response stores instrument identity; source, exchange, receipt
and availability timestamps; payload hash; provider commit; route-contract,
parser, schema and mapping versions; quality/freshness result; redacted request
parameters; raw archive reference and last-good reference.

### 5.4 Exact identity

```text
TrendForge instrument ID
<-> OpenAlgo exchange / symbol / segment / token
<-> instrument type / expiry / strike / option type
<-> lot size / tick size / unit
<-> valid-from / valid-to / mapping source and version
```

No fuzzy match influences research state, quantity or an option vote.

## 6. Research Quantity Contract

Reuse `selection/research_quantity.py`; do not create a second sizing engine.

```text
unitRisk = abs(researchEntry - researchStop) + declaredCosts
riskBudget = researchCapitalInr * researchRiskPct
baseQty = floor(riskBudget / unitRisk)
researchQuantity =
    floorToLot(baseQty * dataQualityCap * regimeCap *
               liquidityCap * calibrationCap)
```

Rules:

- `REJECT`, missing side, missing stop, invalid geometry, unknown lot or stale
  price produces quantity zero with a named reason.
- Quantity is capped by research capital and rounded down to a valid lot.
- Evidence strength never increases quantity.
- Broker funds and broker positions are never read.
- Costs and calibration versions are displayed.

## 7. Corrected R17 Milestones

### R17-B - Provider pin and route manifest

Add a machine-verifiable provider contract to the existing OpenAlgo client and
expose a secret-free read-only contract endpoint.

Acceptance:

- pinned commit and contract version are returned;
- eleven relevant provider REST/stream files are SHA-256 pinned;
- allowed routes are unique and use only POST;
- no forbidden route can enter the allowlist;
- WebSocket limitations are explicit;
- existing capability behavior remains unchanged.

### R17-C - REST client repair and extension

Status: VERIFIED 2026-08-31 against strict local fixtures; no live broker call.

- Parse documented timezone-aware IST history strings.
- Retain numeric epoch fixtures only when explicitly typed.
- Add ping, intervals, quote and multiquote methods.
- Validate identity, numeric fields, OHLC invariants and response size.
- Add bounded retries, per-route rate budgets and circuit state.

Acceptance: populated fixtures pass; empty/malformed/partial/stale fixtures fail
closed; credentials never appear in errors, logs, DTOs, hashes or archives.

### R17-D - Exact instrument binding

Status: VERIFIED 2026-08-31 against strict local fixtures; no live master fetch.

Build one versioned NSE, NFO and MCX mapper. Unknown, ambiguous, expired or
cross-segment identities become `WAIT_IDENTITY`.

### R17-E - Immutable REST replay

Status: VERIFIED 2026-08-31 against the existing content-addressed store and
temporary restart/corruption fixtures; no migration or production-data write.

Reuse the existing raw archive and last-good pointer. Failed, partial or empty
responses cannot replace populated last-good data. Replay reproduces the same
normalized hash.

### R17-F - Stream interfaces and fixtures

Status: VERIFIED 2026-08-31 as a dependency-free transport/state contract; no
socket, credential or provider continuity observation.

Build authentication, subscription, heartbeat, reconnect, resubscription,
bounded queues, duplicate/reorder and discontinuity fixtures. One managed
connection serves the canonical shortlist. Browser-visible symbols may receive
display quotes but cannot alter evidence.

Local receipt sequence is not provider completeness proof. REST fallback opens
a new transport session and cannot repair a stream gap.

### R17-G - Separately approved live observation

After credential and dependency approval:

```text
one REST symbol -> ten REST symbols -> shortlist REST
-> one stream symbol -> shortlist stream -> restart/replay observation
```

Without verifiable provider sequence/replay support, remain
`FIXTURE_VERIFIED / STREAM_SEQUENCE_UNAVAILABLE`.

#### R17-G bounded observer contract

Status: IMPLEMENTED_AND_LIVE_ATTEMPT_BLOCKED 2026-09-01. The approved local
observation reached populated intervals after adding the provider-advertised
`60m` token, then failed closed because the stored Kite session returned
`Incorrect api_key or access_token` for the first quote.

The live observation is an explicit operator-run CLI, not a background service
and not an API activation path. It reuses the R17-B REST client, R17-D identity
mapper, R17-E replay store and R17-F stream state manager.

- read exact identity rows from the supplied OpenAlgo `symtoken` SQLite master
  in read-only mode; never import or mutate the provider database;
- require `OPENALGO_ENABLED=1`, a loopback `OPENALGO_BASE_URL`, and
  `OPENALGO_API_KEY` supplied explicitly for the approved run;
- accept one to ten unique `EXCHANGE:SYMBOL` instruments only;
- call only the eight pinned read-only market-data routes; account, funds,
  holdings, positions, margin, tradebook and order routes remain impossible;
- execute `ping -> intervals -> one quote -> up-to-ten multiquote -> shortlist
  multiquote -> history`, then the server-observed WebSocket authentication and
  `symbols` / `Quote` subscription variant;
- use one managed WebSocket connection, close it on success and failure, and
  reconnect once with a new R17-F session before resubscribing the same exact
  shortlist;
- archive and replay one populated REST quote through the existing
  `MarketDataStore`; no second database or latest-good pointer is introduced;
- emit one redacted JSON report containing route outcomes, exact identity hash,
  stream state, replay hashes and blocker codes, but no API key, cookie, broker
  token, account data or raw credential-bearing request;
- a missing key, missing master row, partial response, failed authentication,
  failed subscription, missing timestamp, stale event or replay mismatch fails
  closed and cannot advance activation;
- because the pinned provider exposes no verifiable provider event sequence,
  even a successful socket observation retains
  `STREAM_SEQUENCE_UNAVAILABLE`; local receipt order is not continuity proof.

#### R17-G observed live attempt - 2026-09-01

The bounded run resolved 10/10 exact NSE equity identities and observed a
populated OpenAlgo intervals response. A TrendForge compatibility gap was found
and fixed: the pinned Kite adapter advertises `60m`, which is a valid history
token but was absent from the client allowlist. Focused and complete regressions
pass after the repair.

The first RELIANCE quote then returned HTTP 500 with `Incorrect api_key or
access_token`. This is an expired/invalid broker-session prerequisite, not
usable market data. The observer therefore wrote no replay row, did not begin
stream acceptance, did not change activation, and remained
`BLOCKED / FIXTURE_VERIFIED / STREAM_SEQUENCE_UNAVAILABLE`. A fresh Kite login
in the existing OpenAlgo UI is required before rerunning this same milestone.
No provider source change is required or authorized by this evidence.
Operator disposition: `POSTPONED_BY_USER` on 2026-09-01. A fresh Kite login is
not part of the current build. Resume R17-G only through this same bounded
observer contract after new explicit approval. Until then, OpenAlgo remains
optional and non-authoritative; R9 intraday ORB/VWAP remains postponed. The next
active File A milestone is R18-A, not another R17 implementation.
Acceptance requires adversarial tests for local-only URLs, ten-symbol bounds,
route allowlisting, identity ambiguity, secret redaction, partial REST results,
server protocol selection, socket close-on-error, reconnect/resubscribe,
deterministic replay and the provider-sequence ceiling. Live status is recorded
only from the separately approved credentialed run.

### R17-H - Shadow projection, option votes and UI

Status: FIXTURE_VERIFIED 2026-08-31. The additive backend DTO, read-only GET
route and Live Ops renderer are implemented. No OpenAlgo credential, REST
request or socket was used.

Show base state, OpenAlgo capability, REST/stream quality and age, dependent
profile ceiling, research geometry and quantity, each option-purpose vote,
option concentration diagnostic, missing/conflicting evidence and the next
required condition. Detailed lineage, formulas and replay references stay in
the inspector.

### R17-I - Controlled activation and rollback

Status: FIXTURE_VERIFIED 2026-08-31. Configuration alone now stops at
`FIXTURE_VERIFIED`; it cannot select `OPENALGO_RO`. Disabled-mode fixtures
prove unchanged canonical output hashes, stopped stream state, and zero
post-disable network/storage activity.

```text
DISABLED -> CONTRACT_PINNED -> FIXTURE_VERIFIED
-> REST_SHADOW_OBSERVED -> STREAM_SHADOW_OBSERVED
-> SHADOW_LIVE only if every required proof passes
```

Turning R17 off restores unchanged R1-R16 output and starts no socket, network
task or persistence write.

Observed checkpoint:

```text
R17-G observer tests:         11 passed
Focused R17 + lane/security:  132 passed
Complete backend:             1,435 passed
Frontend:                     218/218 legacy checks + R17 shadow check
Python compilation / Ruff:    passed / passed
Real master identity:         NSE:RELIANCE = EXACT / EQUITY
No-credential observer:       BLOCKED, FIXTURE_VERIFIED
Disabled GET /shadow:         DISABLED, rows=[], executable=false
Configured-only /shadow:      FIXTURE_VERIFIED, WAIT_REST_OBSERVATION
Configured-only data lane:    FREE_OFFICIAL, canConfirm=false
POST /shadow:                 405
```

This does not complete R17-G. `REST_SHADOW_OBSERVED`,
`STREAM_SHADOW_OBSERVED` and `SHADOW_LIVE` remain unclaimed until separately
approved credentialed observation and replay evidence pass.

## 8. Failure and Acceptance Battery

Test at minimum:

1. absent configuration;
2. configured but disabled;
3. unsafe remote base URL;
4. forbidden route injected into allowlist;
5. duplicate route;
6. secret in serialized payload;
7. HTTP 200 with `{}`;
8. targeted quote with no symbol data;
9. partial multiquote;
10. wrong symbol/exchange;
11. stale quote;
12. IST history timestamp;
13. duplicate/reversed/impossible candle;
14. unsupported interval;
15. oversized response;
16. timeout and bounded retry;
17. rate-limit breaker;
18. market closed/holiday;
19. NSE versus MCX session mismatch;
20. expired contract;
21. ambiguous option identity;
22. crossed/partial option chain;
23. missing Greeks input;
24. PCR denominator zero;
25. max-pain outside usable strikes;
26. unsigned gamma mislabeled as dealer positioning;
27. duplicate option vote ID;
28. separate votes retain chain snapshot lineage;
29. research quantity with invalid stop;
30. research quantity with missing lot;
31. quantity exceeds research capital;
32. stream heartbeat lapse;
33. duplicate/out-of-order stream event;
34. reconnect without replay;
35. REST fallback after gap;
36. queue backpressure;
37. restart during archive write;
38. corrupted replay;
39. disabled R17 changes base output hash;
40. existing collector regression.

## 9. Files and Ownership

Extend:

- `backend/trendforge_api/openalgo_client.py`
- `backend/trendforge_api/source_adapters.py`
- `backend/trendforge_api/main.py`
- `backend/trendforge_api/selection/research_quantity.py`
- existing R12/options claim modules
- existing frontend radar/inspector modules

Add only when its milestone starts: focused R17 tests, one versioned identity
mapping module if no existing owner fits, and one stream manager after
dependency approval.

Do not add another downloader, database, public-state owner, options engine or
quantity engine.

## 10. Definition of Complete

R17 is complete only when disabled mode is inert; provider contracts match
observed behavior; exact identity, timestamps, freshness and replay pass;
research quantity is deterministic and non-executable; separate option-purpose
votes are deterministic, traceable and not described as win probability; live
observation, if approved, passes integrity tests; regressions pass; and status
documents contain observed evidence.

Passing fixtures alone authorizes `FIXTURE_VERIFIED`, not production-ready or
`SHADOW_LIVE`.
