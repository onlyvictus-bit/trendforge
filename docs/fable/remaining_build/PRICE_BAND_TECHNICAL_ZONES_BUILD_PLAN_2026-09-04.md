# Build Plan — Official NSE Price-Band Limits + Technical Price Zones
**Date:** 2026-09-04 · **Status:** PLAN (not executed — assessment only)
**Scope:** (A) official exchange price-band/circuit-limit validation,
(B) separate technical zones (VWAP, Bollinger, pivots, RSI, ATR, candle ranges),
(C) integration into R1–R5 + tradability. Read-only v1: **no broker execution.**
**Authority order:** user instruction > this plan's File A citations > AGENTS.md >
DECISIONS.md (D-066/D-067) > tests > current code. File A controls scope/IDs/ceilings.

## 0. Verified baseline (re-checked 2026-09-04, do not assume otherwise)
- **Checkpoint CONFIRMED (corrected 2026-09-04):** the 2026-09-02 evidence
  lives in the content-addressed normalized store (`data/market_data/`,
  read via `store.latest_for`), not in the SQLite parse tables:
  `nse_price_bands` 3,517 rows @2026-09-02
  (`addab84f…4503cd2`), `nse_esm` 290 rows @2026-09-03
  (`f3c074e6…fb0d7b49c8a`), `nse_auction_securities` NIL valid-empty
  @2026-07-09 (`5c647df6…04ca1a4145`, quarterly cadence: fresh to ~Oct 2026).
  The tradability gate reads this store (`load_restriction_sources`), so the
  Part 1 evidence foundation EXISTS. Follow-up: record in DECISIONS which
  surface is canonical for gates (normalized store) vs archive (SQLite parse
  tables), since the latter hold zero rows for these keys.
- Stale lineage: bhavcopy EOD 2026-08-03, fno_ban 2026-08-24 (1 row),
  fo_bhavcopy 2026-08-21, index 2026-08-28, filings 2026-07-30.
  `R5_STRUCTURE_NOT_READY` is correct behavior.
- `sourceActivationReady=false`, MWPL unproven, compiler permission 0 — intentional lock.
- Registry cites `selection/relative_strength.py` (FTR-004, FTR-037) and routes
  `/api/selection/features/{relative-strength,volatility}`, `/api/selection/sector-rotation`
  — **file absent, routes unregistered, lint does not verify owner/route claims.**
- Existing anchors to reuse: `feature_engineering.py:66-105` (returns/ATR14/RVOL20/
  vwap20Distance), `institutional_features.py:77-82,201-210` (_rsi, MACD,
  bollinger_width, session VWAP), `selection/structure.py:140` true range,
  `scanners/native_extended.py:83` close-range ATR, S3 `rs_1d/rs_5d`,
  S5 delivery statuses (`DELIVERY_Z_PIT20`, `CURRENT_PCT_*`,
  `UNKNOWN_MISSING_SOURCE`, `FORBIDDEN_ON_INTRADAY`).
- Tradability cascade already implements PASS/WAIT/REJECT with epsilon +
  proximity (`selection/tradability.py:277-341`); `current_price` is an
  untyped caller map (`:798`) — must become provenance-typed.
- R5 rebuild path: scheduler `market_data_scheduler.py:544` →
  `persist_r5_structure_batch` → readers via `_hash_matched_r5_or_503`
  (`main.py:1630`). No code change needed for R5 — only a successful run.

## 1. First principle (non-negotiable)
`EXCHANGE_LIMIT` (official NSE upper/lower hard limits) and `TECHNICAL_ZONE`
(VWAP/BB/pivots/RSI/ATR/extremes research features) are different universes:
a technical indicator must never authorize trading outside an exchange limit,
convert missing limits into PASS, or count as a second confirmation of the
official source. Tradability PASS is non-voting (D-066).

## 2. Official NSE rule matrix (primary sources; mirrors flagged [M])
- EQ cash non-F&O: 2/5/10/20%, CE mutual funds 10%; revision **down daily, up
  bi-monthly**; 40% exists via SURV circulars [M for 40% text]. Base = prev
  close. Sources: nseindia.com *Price Bands*, *Daily review*, CM Reg Part-A 2.5.
- F&O underlyings: no fixed band; **dynamic 10% operating range**; flex at
  last-trade >=9.90% (then 14.90%...); **50 trades / 10 UCCs / 3 TMs each
  side**; flex **5%/3%/2%** with cooling **15(5 in last 30m)/30/60 min**;
  **SLIDING** both sides, stale-side orders cancelled; **midpoint-abort** in
  cooling; options temp floor/ceiling via LPP. Sources:
  SEBI/HO/MRD/TPD-1/P/CIR/2024/58 (2024-05-24); NSE/CMTR/63404, 62237, 64626;
  NSE/FAOP/62241, 63405, 64627, 64995.
- Index MWCB: 10/15/20% Nifty-or-Sensex-first; halts 45m/<1pm, 15m/1–2:30pm,
  none after (10%); 1h45/<1pm, 45m/1–2pm, rest-of-day after (15%); 20% rest
  of day; 15-min pre-open after each halt. Base = prev-day index close,
  translated daily. Source: SEBI CIR/MRD/DP/25/2013.
- T2T (BE/ST/BZ/SZ): **5% or lower** on shift; exit keeps 5% to next review;
  fortnightly in, quarterly out; intraday forbidden; IPO/TFT 10 days.
  Sources: NSE segment + movement-review pages; e.g. NSE/SURV/73085.
- IPO/relist day 1: <=250cr **5%**, >250cr **20%** of equilibrium (else issue)
  price; TFT 10 days. Source: SEBI master Ch.1 2.6.2.
- GSM: 6-stage current framework (older FAQ shows 4 — use dated rows);
  invariant **T2T + band <=5%**, 100% margin, weekly→monthly, ASD 50→200%,
  Stage VI no-up-move. Sources: NSE GSM page; NSE/SURV/64402.
- ESM (<1000cr, excl PSU/F&O): Stage I T2T + **5% (2% if already)** + 100%
  margin T+2; Stage II T2T + **2%** + 100% margin + **PPCA all days**; weekly
  review; 90-day floor. Sources: NSE/SURV/56948; NSE/SURV/57609; 2025-07-25
  revision.
- PPCA illiquid: quarterly in/out (<10k vol AND <50 trades/day, all
  exchanges); 6x1h sessions (45m entry/random close); **max 20%** (reducible);
  OHLC from equilibria; MW-halt cancels/purges. Sources: SEBI
  CIR/MRD/DP/38/2013; CIR/MRD/DP/21/2010; BSE PPCA FAQ.
- Tick (CM): <250 Rs **0.01**, >=250 Rs **0.05**, monthly review; futures
  mirror underlying; options 0.05; upper slabs rise post-2025-04-15 **[M only
  — needs NSE primary]**. Sources: NSE circular 66/2024 (eff. 2024-06-10);
  NSE/CMTR/67133 + FAOP/67134.
- SME fixed %: **UNVERIFIED — NSE-primary evidence required.**
- Auction market: 20% (NSE price-bands page).

## 3. Exchange-limit source and calculation contract
No free public artifact carries exact rupee limits (member-only EOD DB files
do). Contract = calculated geometry, proven inputs only:
`EXCHANGE_LIMIT(symbol,date)` = parse official archive (complete-list / SURV
circular / ESM release / auction list) -> rule class {FIXED(p), NONE_FNO,
MWCB, PPCA, TFT5, IPO_DAY1} -> `basePrice` = official prev close
(CA-adjusted via R14; None if CA-unresolved) -> bandPct from table 2
(F&O flex state unknowable offline -> use start-of-day 10% and label
`DYNAMIC_FLEX_UNKNOWN_INTRADAY`) -> raw lo/hi -> align DOWN/UP to monthly tick
grid (tick-master required; open if missing) -> stamp
`{basePrice,bandPct,tickGrid,sourceContentHash,dataDate}` or WAIT.
Any unproven input -> `WAIT_*`, never pass-through. New FTR rows only if new
feature IDs are introduced; prefer reusing existing contract rows.

## 4. Technical-zone feature contracts (all `can_support_confirmed=false`)
New `selection/session_vwap.py` (anchored 09:15 IST session VWAP + anchored
variant; partial session -> UNAVAILABLE) and `selection/technical_zones.py`:
VWAP deviation (weighted variance, ±1/2 sigma, PARTICIPATION cap shared with
RVOL), Bollinger 1/2/3 sigma (lookback 20, ddof=0 pinned), ONE classic-floor
pivot family (harmonic multi-sensitivity stays display-only in
`harmonic_advanced.py`), RSI(14) via `institutional_features._rsi` (context
bands only, no auto signals), ATR regime = Wilder smoothing period 14
(matches `r16_pit._atr14` and FTR-016), 1y/2y extremes = P95/P99 +
ATR-normalized ranges (raw max never gates), EOD closed bars only,
PIT-adjusted history only, separate INTRADAY/SWING params (intraday params
dormant until verified bars exist — R9-skipped stands).
Each row records: purpose, horizon, inputs, formula, units, lookback,
freshness, owner, CA handling, failure code, family, group, storage/API/UI
fields, T-IDs.

## 5. Intraday vs swing table
SWING: A4 adjusted closed sessions; base = prev official close; VWAP
20/60-session anchored + bands; S5 delivery as gate; auction N/A; all six
features computed. INTRADAY: verified read-only bars only (absent -> R9
skip holds); start-of-day 10% width, flex UNKNOWN; session VWAP only,
partial -> UNAVAILABLE; delivery FORBIDDEN (existing); PPCA rows WAIT;
same formulas with separately versioned intraday params; unclosed bar ->
INPUT_INCOMPLETE.

## 6. Lineage, freshness, PIT
Collector -> immutable archive -> strict parser ->
`source_parse_results` + snapshots + structured rows -> windows (bands 2d,
ESM 8d, auction 93d; ADD tick-master monthly + flex-state UNKNOWN) ->
R14-adjusted history -> features with `{featureVersion,
engineId=trendforge.numpy-pandas v1.0.0, warmup}` -> R5 claims (PIT envelope
mandatory) -> S7 -> S8 blob. `data_date` must equal expected session date or
`WAIT_STALE_DATA`. New frozen table `technical_zone_snapshots(run_id, symbol,
feature, version, value_json, bar_hash)`; append-only.

## 7. Anti-double-counting (FUS-009 stays the only vote-shaper)
VWAP-dev + RVOL share one PARTICIPATION rep; BB/ATR/extremes/pivots are
STRUCTURE descriptors under existing groups (no new voting group without File
A amendment); RSI is context text; raw-max never represents. Enforced by a
unit test asserting <=1 supporting claim per family per symbol (mirror the
R13 twin-test pattern).

## 8. Deterministic gate pseudocode (extends current cascade, keeps all codes)
Resolve limit or WAIT (missing/stale/CA-unresolved/flex-unknown/MW-halt);
halt/suspend/GSM>=3/ESM2+intraday/active-ban/locked-band/tender-violation ->
REJECT; price outside [lo,hi] with epsilon=max(tick, price*1e-4) ->
REJECT_PRICE_BAND_LOCKED; edge distance <=1% (or one tick if tighter) ->
WAIT_PROXIMITY; no aligned official close -> WAIT_PRICE_FOR_BAND_CHECK;
else PASS (non-voting). Technical descriptors attach AFTER the gate and can
never change its outcome.

## 9. R5 + rebuild flow
Scheduler R5 block -> persist -> readers via `_hash_matched_r5_or_503`.
Today's gap closes with one successful scheduler run on fresh lineage — no R5
code change. Add gate-hash citation into R5 `why_wait` when band-WAIT
(S8 already stores the gate hash per D-066).

## 10. Modules / storage / APIs / frontend
Parsers: reuse + tick-master parser + R14-aware base-price loader.
New: `selection/session_vwap.py`, `selection/technical_zones.py`.
Storage: `technical_zone_snapshots` table.
APIs: `GET /api/v1/selection/technical-zones{,/{symbol}}` (POST 405, typed
503s); band geometry inside tradability payload as
`geometry{lo,hi,base,rule,tickGrid,hash}` or explicit WAIT codes.
Frontend: inspector-only descriptors; NO new All-Stocks columns;
proximity/lock chips reuse existing chip slots; acceptance pins `<th>` set.

## 11. Coding style (house law, observe exactly)
- Frozen pydantic `BaseModel`, `model_config = MODEL_CONFIG`
  (`alias_generator=to_camel, populate_by_name=True, frozen=True`);
  `StrEnum` reason codes `WAIT_*` / `REJECT_*` / `PASS_*`;
  `model_validator(mode="after")` `enforce_*` raising on ceiling breach.
- Run identity: `run_hash = sha256(sorted-keys JSON identity)` then
  `run_id = stable_id(prefix, *lineage_ids, run_hash)`; datetimes UTC-aware,
  session logic in IST; prices as float with epsilon rule (section 8).
- Validators fail closed: unknown input -> WAIT/INPUT_INCOMPLETE, never
  defaults that look like data.
- Tests first (AGENTS.md workflow): unit + TestClient route tests; fixtures in
  `hybrid_v2/tests_support`; monkeypatch `storage.DB_PATH` to tmp; full
  backend suite + `node frontend/tests/acceptance-check.js` before done.
- Ruff clean; no `place_order`-adjacent strings outside `guidance_oms.py`;
  no Combined_Score/win-probability labels anywhere.
- GATES.md per milestone with CHECK/EXPECT/CWD; record observed results in
  VALIDATION.md and deltas in BUILD_STATUS.md/DECISIONS.md (D-0xx).

## 12. Fifty adversarial tests (write all; grouped)
Parser/hostile (1-10): HTML-as-CSV; missing columns; No-Band-vs-empty;
40% row; unknown band text; band>40/negative; NIL-vs-empty-no-NIL; dateless
URL; duplicate symbol+series; 4k-row perf bound. Geometry (11-20): tick
rounding both sides; sub-250 vs 250+ grids; monthly tick changeover;
CA-day-without-R14 WAIT; split-adjusted base; zero/negative close;
flex-unknown intraday; expired contract; 52w off-by-one; partial-session
VWAP refusal. State (21-30): locked REJECT; proximity both sides; T2T
intraday; GSM threshold; ESM2 intraday; PPCA intraday-vs-swing; MW-halt;
suspended; relist TFT; IPO size paths. Lineage (31-40): stale windows x3;
hash drift w/o date change; data_date/session mismatch; R1/R2/R5 mismatch;
S8 replay identity incl. gate hash; IST/UTC edges; restart idempotency;
content-hash dedupe. Fusion/UI (41-50): zone-cannot-clear-WAIT; one-rep
per group; RSI/BB/extremes non-voting; raw-max ignored; win-prob leak scan;
place_order absence scan; POST 405s; `<th>` freeze; registry owner/route
reality check.

## 13. Real-time failure behaviors
Stale -> dated WAIT (never last-known-as-current); wrong base -> CA-guard
WAIT + quarantine; CA event -> adjustment_version or WAIT; bad tick -> row
quarantine; partial session -> VWAP UNAVAILABLE; unclosed bar ->
INPUT_INCOMPLETE; halt -> REJECT + PPCA cancel/purge semantics; mid-day
band revision -> recompute with new hash, never mutate stored rows; missing
tick master -> geometry WAIT; IST comparisons with UTC-stamped lineage;
restart -> content-hash idempotent resume.

## 14. Smallest safe sequence + gates
1. Checkpoint confirmation: assert `store.latest_for` hashes + row counts for
   the three keys (DONE 2026-09-04 — hashes pinned in §0; STOP if a rerun ever
   diverges). Record the canonical-surface decision (normalized store for
   gates, SQLite as archive) in DECISIONS.md.
2. Tick-master parser + base-price loader; tests 1-20.
3. EXCHANGE_LIMIT geometry in `_price_band_component` (+ flex-unknown, MW-halt,
   PPCA-band paths); S7 suite green; live 200 honest.
4. Zone module + table + APIs; per-feature contract tests.
5. S7/S8 wiring (gate-hash citations, replay test); full suite + battery.
6. Frontend chips + acceptance; docs + registry errata + CSV evidence update.

## 15. KEEP / IMPROVE / ADD / POSTPONE / REJECT
KEEP: strict parsers; classification-only authority; NIL valid-empty; full
cascade + epsilon/proximity; GSM/ESM staging; EOD-only delivery; S7 sole
owner; hash-matched spine. IMPROVE: tick-master + flex-state windows;
provenance-typed `current_price`; registry owner/route corrections.
ADD: tick parser, base loader, VWAP + zone modules/table/APIs, per-symbol
geometry, 50 tests, guidance copy. POSTPONE: intraday zones, options
LPP/cooling, live flex tracking. REJECT: band%-implies-PASS, zone votes or
repairs, COMEX/global proxies, second pipelines/DBs, probability labels,
broker execution.

## 16. Unresolved (evidence needed, do not build on assumptions)
Q1 checkpoint-vs-DB mismatch — **RESOLVED 2026-09-04:** evidence confirmed in
the normalized store (hashes in §0); remaining action is documenting the
canonical-surface decision, not rerunning collectors. Q2 upper-slab
tick table NSE-primary. Q3 SME fixed % NSE-primary. Q4 40% mechanics
NSE-primary. Q5 registry-lint owner/route rule (propose; do not hand-edit
registry yet). Q6 MWPL % standing. Q7 activation approval + fresh five-source
lineage standing.

