# GLM / OPEN-MODEL BUILD PROMPT — Make M-Factor *useful*
## Wire R5 + other live families into FUS-009 · two-sided BUY/SELL · four horizons fail-closed · production-ready screening (not a fake trader)

Copy **this entire file** into GLM. Think first. Do not invent a Combined_Score, a win rate, qty, or a CONFIRMED unlock.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. Chain with `;` not `&&`.

**Date of this prompt: 2026-08-23.**  
**Prior prompt `M_FACTOR_LIVE_UI_OPENCODE_PROMPT.md` is DONE for UI+BFF paint. Do not rebuild the empty BFF. This ticket is the *usefulness* slice: real families, real shorts, honest horizons.**

R5 closed-bar **structure evidence is already built** (`r5_live.py` + `structure.py` FTR-006 / FTR-007 / FTR-017). Live R5 rows remain `structure_state=WAIT`, `can_support_confirmed=False`. **“R5 is ready” means: consume those claims/setups. It does not mean CONFIRMED or an order.**

---

## 0. Why the current M-Factor is not useful (measured 2026-08-22 live DB)

`GET /api/v1/tools/m_factor` works. UI `frontend/m-factor-live.js` paints it. Tests: `test_m_factor_bff.py` 16 passed.

Live swing batch (`limit=40`, tradingDate `2026-08-21`):

| Board | Count | What was wrong |
|--------|--------|----------------|
| BUY | 40 | `longStrength` **23.71–24.93** (flat). `shortStrength` **0**. Class Bull. State **WAIT**. |
| SELL | **0** | No bearish claims exist |
| WAIT | 40 | Neutral just under the +20 band |
| intra / position / commodity | **0 rows** | Correct WAIT codes, empty boards |

Root cause (read these before coding):

1. `selection/r3_claim_adapter.py` emits **one** `EvidenceClaim` (`FTR-040`, family **PARTICIPATION**, direction = R2 `evidence_direction`, strength = `attention_priority`).
2. `live_profile()` **requires STRUCTURE**, weight 0.30. No STRUCTURE claim → stays **0** (FUS-009 does not renormalize).
3. Participation weight **0.25** × ~1.0 → display points cluster near **25**. Rank is noise.
4. Bearish `resolve_evidence` sees no bearish claim → shorts die → no SELL board.
5. `m_factor_bff.py` paints `SETUP_READY` from `r5.detected_setups` while `how` still says `STRUCTURE_NOT_EVALUATED` because FUS-009 never received R5 claims.
6. Universe is **2633 cash** names, not eligible NSE F&O.
7. `index_conflict` is hardcoded `False` (`INDEX_CONFLICT_EVALUATION_NOT_WIRED`).
8. `what` is hardcoded `NO_NAMED_EVENT_EVIDENCE`.
9. Intra/position/commodity **must stay empty** until their own data_mode exists. Copying swing rows onto those boards is a **fail**.

**Done for this ticket means screening is useful:** BUY and SELL both populated when evidence exists; rank_strength **spreads**; debug families show non-zero STRUCTURE when R5 accepted a breakout; `how/what/where/when` cite real claim IDs; other horizons still fail-closed with typed codes. Public state remains WATCH/WAIT/REJECT. **0 CONFIRMED. qty=null. Track sampleCount=0.**

---

## 0.1 Folder law (production vs delete)

| Kind | Path | This ticket |
|------|------|-------------|
| **Keep — claim adapter (new)** | `D:\TrendForge\backend\trendforge_api\selection\m_factor_claims.py` | Merge R3 cash + R5 structure + optional A5/event/FO into one `tuple[EvidenceClaim, ...]` per symbol. Do **not** stuff this into `r3_claim_adapter.py` (that file remains the cheap cash adapter for live R3 persistence). |
| **Keep — BFF compose** | `...\selection\m_factor_bff.py` | Consume `m_factor_claims.py`. Do not recompute FUS-009 weights. |
| **Keep — API** | `...\trendforge_api\main.py` | Route already exists. Do not add POST. Maybe query `universe=fo|cash` if you add F&O filter. |
| **Keep — R5** | `...\selection\r5_live.py`, `structure.py` | **Read.** Persist or rebuild claims from `analyze_closed_bar_structure` **without** changing R5 ceiling. Prefer a **pure function** that turns a hash-matched `R5StructureRowV1` + bars/source into claims (same FTR-006/007/017 as `structure.py`). Do **not** rewrite `analyze_closed_bar_structure` unless a bug blocks claim rebuild. |
| **Keep — tests** | `D:\TrendForge\backend\tests\test_m_factor_bff.py` **and** new `tests/test_m_factor_claims.py` | Golden FUS-009 equality, two-sided boards, horizon empty, no fixture numbers, no CONFIRMED |
| **Keep — frontend** | `D:\TrendForge\frontend\m-factor-live.js` | Show new family bars / SELL cards / F&O toggle if DTO adds fields. Cache-bust `?v=` in `index.html` |
| **Keep — docs** | `docs/BUILD_STATUS.md`, `docs/VALIDATION.md` | Commands + honest counts |
| **Throwaway** | `D:\TrendForge\delete\m_factor_wip_2026-08-23\` | curl dumps, notebooks, failed adapters, one-off scripts, “tmp_probe.py”. **Never** leave those in `backend/tests/` |
| **Do not touch** | `resolver.py` FUS-009 math, `attention_order.py` rank law, File A, Hybrid overlay `p̂`, `sourceActivationReady` | |

If a file is experimental and you are unsure: write it under `delete\m_factor_wip_2026-08-23\` first, then promote the winner into `selection/`.

---

## 1. Authority (File A wins)

| Rank | File | Use |
|------|------|-----|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` FUS-009, FTR-006/007/017/020/040 | Families, no renormalize, R5 cannot unlock CONFIRMED |
| 2 | `AGENTS.md` | Research-only, HTTP 200 ≠ usable, no broker |
| 3 | `docs/fable/FINAL_MERGE_PLAN.md` FMR-010 | long/short **exactly** two FUS-009 outputs; class ≠ readiness ≠ state |
| 4 | `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` §1D | Scanner; F&O profile; BFF cannot independent-score |
| 5 | This file | Execution order and folder law |
| 6 | Live code listed in §2 | Ground truth |

Conflict: stricter fail-closed / non-probability / no-qty wins.  
Hybrid V2 overlay (`s4s5_compare`, Kelly) is **not** an M-Factor input.

**R5 “confirm” clarification (do not hallucinate):**  
User instruction “R5 confirm is already built” means **closed-bar detection + claim construction in `structure.py` exist**. Live `R5StructureRowV1.can_support_confirmed` is **False**. `r5_live.py` module docstring: no CONFIRMED, no qty. You **wire those claims into FUS-009**. You **do not** set `can_unlock_confirmed` or emit CONFIRMED from M-Factor.

---

## 2. Already live — READ, do not rebuild

```
selection/inventory_source_bundle.py     R1 cheap features + hashes
selection/attention_order.py             R2 public_state, attention_priority, evidence_direction
selection/r3_live.py                     persisted FUS-009 diagnostic; live_profile() weights
selection/r3_claim_adapter.py            FTR-040 cash participation ONLY (keep for R3 persist)
selection/resolver.py                    FUS-009 (max per group, no renormalize)
selection/structure.py                   analyze_closed_bar_structure → FTR-006/007/017 claims
selection/r5_live.py                     latest_r5_structure_batch(); setups; claim_ids; WAIT ceiling
selection/r14_live.py                    CA join; WAIT_CA veto
selection/r4_live.py                     identity pin
selection/index_a5_context.py            latest_cash_context()
selection/fo_a6_enrichment.py            latest_fo_enrichment()
selection/r6_live.py                     named deals / AMFI stickers (display); not a second ranker
selection/m_factor_bff.py                BFF + boards + empty horizons
selection/evidence_radar/calculate.py    named_deal_fact() pattern for EVENT
frontend/m-factor-live.js                live owner of #tool when m_factor
GET /api/v1/tools/m_factor
GET /api/v1/selection/resolution
GET /api/v1/selection/structure
GET /api/v1/selection/ca-join
```

Python: `D:\TrendForge\.venv\Scripts\python.exe`  
Tests: `cd D:\TrendForge\backend; ..\.venv\Scripts\python.exe -m pytest tests/test_m_factor_bff.py tests/test_m_factor_claims.py -q`

---

## 3. What to connect (data inventory)

Each row is one **typed slot**. Missing → named WAIT/UNKNOWN, **not** skip, **not** extra vote.

| Slot | Live source | Grain | Family / group | How it enters FUS-009 | Illegal use |
|------|-------------|-------|----------------|------------------------|-------------|
| **HOW price** | R5 `detected_setups` + `structure.py` claims FTR-006 (breakout accept), FTR-007 (NRx) | Per symbol, closed bars, hash-matched R1/R2/R14 | STRUCTURE / `CG_PRICE_STRUCTURE` and `CG_COMPRESSION` | Rebuild claims from hash-matched R5 row; direction = R5 `evidence_direction` (bullish vs bearish hypotheses pick supporting vs opposing) | Do not use unclosed bars; do not set CONFIRMED |
| **HOW money (cash)** | R3 adapter FTR-040 + R2 attention_priority | Same cash session as R1 | PARTICIPATION / `CG_ACTIVITY_SESSION` | Keep **one** cash-activity representative | Do not add R5 FTR-017 RVOL **and** FTR-040 if they share `CG_ACTIVITY_SESSION` — **max() in group**, but still do not mint duplicates if they are the same root. Prefer: FTR-040 = cheap discovery; FTR-017 = R5 completed-bar RVOL. If correlation_group is the same, FUS-009 already maxes. Verify in debug. |
| **WHAT event** | R6/radar `named_deal_fact` / official bulk-block last-good | Named client + side + date | EVENT_AND_SPONSOR / `CG_EVENT_ROOT` | Claim only if a **named** deal row exists for the symbol | `nse_fii_dii` market net ≠ “FII bought RELIANCE”. AMFI delayed ≠ intra |
| **WHERE identity** | R1 stock record + R4 pin | instrument_id | eligibility, not a vote | Unresolved identity → no board seat | Numeric scrip / UNKNOWN_ID skip |
| **WHEN** | `available_at`, `trading_date`, freshness | snapshot | metadata | Mix hashes → 503 `WAIT_MIXED_SNAPSHOT` | |
| **SAFE** | R2 REJECT, R14 WAIT_CA, ban/MWPL if present | veto | TRADABILITY | Hard veto **before** rank | Safety as a +rank bonus |
| **WHERE market** | A5 `latest_cash_context()` | index/sector | MARKET_AND_SECTOR_CONTEXT | Context claim or INDEX_CONFLICT when stock Strong Bull vs required bearish index | Index as a second stock vote |
| **FO OI** | `latest_fo_enrichment()` + FTR-020 four codes | F&O contract/expiry | DERIVATIVES — **one package** | Optional SUPPORT/WEAKEN on F&O universe only; cannot create cash direction | “Long buildup”; participant OI as stock sponsor |
| **Intra bars** | Not activated | — | — | Horizon stays empty | Dress EOD as ORB |
| **Position weekly** | Not wired | — | — | Horizon stays empty | AMFI “bought today” |
| **MCX local** | `mcx_contracts.py` / commodity context | MCX | — | Horizon stays empty until local master+price+OI | CFTC/WGC minting a commodity BUY |

---

## 4. Data flow (production)

```text
R1 bundle (hash) ──┐
R2 attention ──────┼── hash match or 503 WAIT_MIXED_SNAPSHOT
R3 resolution ─────┤  (equality check vs recomputed direction-run MUST remain)
R14 ca-join ───────┤  WAIT_CA → veto, hide AS/z elsewhere; here: no STRUCTURE vote from broken CA
R5 structure ──────┘  hash-match R1+R2 (+R14 as R5 already requires)

Per symbol:
  claims = []
  + cash FTR-040 from r3_claim_adapter (existing)
  + R5 FTR-006/007 (STRUCTURE) rebuilt from analyze_closed_bar_structure OR stored claim_ids+metrics
  + R5 FTR-017 (PARTICIPATION RVOL) if group distinct or let FUS-009 max
  + EVENT named-deal claim if official row names symbol
  + A5 context claim if present (cannot invent direction)

  long_run  = resolve_evidence(BULLISH,  claims, live_profile, gates)
  short_run = resolve_evidence(BEARISH, claims, live_profile, gates)

  longStrength  = round(long_run.evidence_strength * 100, 2)
  shortStrength = round(short_run.evidence_strength * 100, 2)
  mBalance      = long - short
  rankStrength  = max(long, short)
  class         = M_FACTOR_CLASS_V0(mBalance)

  board = assign_board(...)   # existing; REJECT/INDEX_CONFLICT → wait
  readiness = SETUP_READY only if STRUCTURE selected support exists
              (not merely r5.detected_setups string)

  geometry entry/stop/t1/t2/quantity remain None
           (R5 metrics.reference_level may appear in `how` / labels, NEVER as an order)

Horizon != swing:
  return empty boards + HORIZON_WAIT_CODES (already implemented). Do not fill.
```

**Function flow (names you should actually write):**

```text
load_m_factor_lineage()           # already _load_lineage in m_factor_bff.py
rebuild_r5_claims(r5_row, ...)    # NEW in m_factor_claims.py
merge_symbol_claims(...)          # NEW: cash + r5 + event + a5
build_m_factor_batch(...)         # EXISTING: call merge, then two resolve_evidence
assign_board / directional_class  # EXISTING
GET /api/v1/tools/m_factor        # EXISTING
TrendForgeMFactorLive.load()      # EXISTING frontend
```

Do **not** persist a second R3. Do **not** change `build_r3_resolution` outputs unless a test proves persisted R3 must stay the cheap diagnostic (it should). M-Factor may **compose a richer claim set than persisted R3**. Then FMR-010.1 “long/short equal two FUS-009 outputs” means **equal the two resolve_evidence calls you just ran**, not equal the thin persisted R3 row.

**Critical test change:** today `m_factor_bff.py` **fails** if recomputed direction-run ≠ persisted R3 (`WAIT_MIXED_SNAPSHOT`). That check is correct **only while M-Factor uses the same claim set as R3**. Once you add R5 claims, **drop that equality against persisted R3** and replace with:

- Persisted R3 still hash-matches R1/R2 (lineage).
- M-Factor long/short equal **its own** two `resolve_evidence` calls (deterministic, golden fixture).
- Optional debug field `r3EvidenceStrength` vs `mFactorDirectionStrength` so the inspector shows “R3 cheap vs M-Factor fused” without mixing them.

Document this in BUILD_STATUS. Do not silently change FMR-010 meaning.

---

## 5. Code / folder structure (future-proof)

```
backend/trendforge_api/selection/
  m_factor_claims.py          # NEW — claim merge only
  m_factor_bff.py             # EDIT — compose + boards
  r3_claim_adapter.py         # READ; do not overload
  r5_live.py / structure.py   # READ; rebuild claims from same FTRs
  resolver.py                 # READ-ONLY math

backend/tests/
  test_m_factor_claims.py     # NEW
  test_m_factor_bff.py        # EDIT existing 16 tests

frontend/
  m-factor-live.js            # EDIT if DTO grows (families on by default for selected card)
  index.html                  # bump ?v=20260823-mf3 on m-factor-live.js

docs/fable/remaining_build/
  M_FACTOR_USEFUL_FUS009_WIRING_GLM_PROMPT.md   # THIS FILE (authority for the ticket)

delete/m_factor_wip_2026-08-23/
  README.txt                  # already the dump zone
  probe_*.py, *.json          # all scratch
```

One module = one job. `m_factor_claims.py` must not import FastAPI. `m_factor_bff.py` must not fetch URLs.

---

## 6. Behaviour checks (must observe, not claim)

Run after each slice:

```powershell
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_m_factor_claims.py tests/test_m_factor_bff.py -q --tb=short
cd D:\TrendForge\frontend\tests
node acceptance-check.js
```

Live probe (put scripts in `delete\m_factor_wip_2026-08-23\` if temporary):

```text
build_m_factor_batch(horizon="swing", side="both", limit=40, debug=True)
```

**Pass when:**

| Check | Expected |
|--------|----------|
| STRUCTURE family `support_strength` | > 0 on symbols whose R5 `detected_setups` includes CLOSED_BAR_BREAKOUT and hashes match |
| `shortStrength` | > 0 on some BEARISH R2 names → **sellRows non-empty** if class Bear/Strong Bear |
| Rank spread on BUY40 | **not** stuck in a 1-point band (document min/max in VALIDATION.md) |
| `readiness_tag=SETUP_READY` | only if a STRUCTURE support claim is selected |
| `how` | cites FTR-006/007 or explicit STRUCTURE_NOT_EVALUATED |
| `what` | named deal code or UNKNOWN_NO_LARGE_DEAL_ROW — not a hardcoded sentence for all rows |
| `entry/stop/t1/t2/quantity` | still **null** |
| `publicState` | never CONFIRMED |
| intra | 200 + `WAIT_HORIZON_INTRADAY_NOT_ACTIVATED` + empty boards |
| position | `WAIT_HORIZON_POSITION_NOT_WIRED` + empty |
| commodity | `WAIT_HORIZON_COMMODITY_MCX_LOCAL_NOT_WIRED` + empty |
| POST /tools/m_factor | 405 |
| mixed R5 hash | withhold STRUCTURE claims; do not 200 mixed geometry |
| fixture strings | no `FIXTURE-20260729-1042`, no 168.9 |
| Track | sampleCount 0, winRate null |
| Frontend | SELL cards appear when sellRows exist; horizon switcher still shows WAIT codes |

**Fail if:** you filled intra with swing rows; you set sourceActivationReady; you called OI “long buildup”; you used AMFI on intra; you put CFTC names on commodity; you wrote probes into `backend/tests`.

---

## 7. Expected output (user-visible)

Discovery → **M** → horizon **swing**:

- Hero: live `runId`, IST cutoff, ceiling WAIT, **not** fixture chip.
- Signals: market strip (adv/dec already from R1); long/short bars of **selected** row; rank table; **BUY and SELL** decision panels; levels **PENDING**.
- How validated: layers PASS/PARTIAL/WAIT from **gates**, not copy.
- Track: locked.
- Engines: resolver ONLY RANK OWNER; R5 DIRECTION OWNER; PK no vote.

Intra / position / commodity tabs: explicit WAIT code, **zero** cards. That is production-ready honesty.

Optional query: `?universe=fo` filters `latest_fo_enrichment` / F&O eligible instrument_ids. Default can stay cash EOD until FO identity is proven per row; do not silently drop 2633 to 0.

---

## 8. Slice order (ship each)

1. `m_factor_claims.py`: rebuild R5 STRUCTURE claims; unit tests with a fixture R5 row that has `accepted=True`.  
2. Merge + two `resolve_evidence`; BFF uses merge; **replace** R3-equality check as in §4.  
3. Golden: same claims → same long/short; adding FTR-006 increases long (bullish) or short (bearish) vs cash-only.  
4. Named-deal EVENT claim via existing `named_deal_fact` / R6 loaders; UNKNOWN if none.  
5. A5 INDEX_CONFLICT evaluation (stock Bull + required bearish index → wait seat).  
6. Frontend: SELL grid + family debug on selected card; bump cache `?v=`.  
7. **Stop.** Do not implement intra/position/MCX boards in this ticket.

---

## 9. Stop-if

Stop and report if:

- Wiring R5 would require `can_support_confirmed=True` on live rows.  
- You cannot rebuild FTR-006 without re-fetching bars and R14 WAIT_CA is set (then STRUCTURE = withheld, code `WAIT_CA`).  
- Persisted R5 hashes do not match R1/R2 (withhold, don’t mix).  
- You feel the need for a second weighted score to “make ranks look spread.” Spread must come from **real families**, not a fudge.

---

## 10. After merge

- Update `docs/BUILD_STATUS.md` with min/max rankStrength, buy/sell/wait counts, tradingDate.  
- Update `docs/VALIDATION.md` with pytest commands.  
- Move all probe scripts into `D:\TrendForge\delete\m_factor_wip_2026-08-23\`.  
- Leave empty-horizon tests **green**.

You are done when a trader can use swing M-Factor to **pick names to inspect** with a real long vs short split — still WAIT, still no order — and the other three horizons stay honestly empty.
