# OPEN-MODEL BUILD PROMPT — M-Factor live UI

> **2026-08-23:** UI + `GET /api/v1/tools/m_factor` **shipped**. Do **not** execute this file as a greenfield build. Next GLM ticket: `M_FACTOR_USEFUL_FUS009_WIRING_GLM_PROMPT.md` (wire R5/other families so ranks spread and SELL exists).

## Paint the existing tool room · Signals / How validated / Track record / Engines used · Stock decision panels · four horizons × BUY and SELL · how / what / where / when

Copy this **entire file** into the implementing model. Think first to find a Combined_Score, a win rate. Do not invent a second M-Factor nav, or a CONFIRMED unlock.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. Shell: PowerShell. Chain with `;` not `&&`.

**Verified 2026-08-22 against live `frontend/index.html`, `frontend/app.js`, `frontend/product-fixture.js`, `backend/trendforge_api/selection/r3_live.py`, `selection/resolver.py`. There is no `GET /api/v1/tools/m_factor` today.**

---

## 0. What you are building (and the lie it forbids)

You are  building a buy/sell fire scanner helper.

You **are** wiring the **already-present Discovery → M-Factor UI** to a **read-only BFF** that projects **two File A `FUS-009` hypotheses** (bullish + bearish) onto:

| UI surface (already in DOM) | ID / selector | Must show |
|---|---|---|
| Tool room | `section#tool` | M-Factor only when `data-tool="m_factor"` |
| Hero | `#toolEyebrow` `#toolTitle` `#toolPurpose` `#toolState` | Live ceiling, live `run_id`, IST cutoff — **not** `FIXTURE-20260729-1042` |
| **Signals** tab | `.tool-tab[data-evidence="signals"]` → `#toolContent` | Rank table + evidence bars + **Stock decision panels** |
| **How validated** tab | `[data-evidence="validation"]` | Six layers + per-row PASS/PARTIAL/WAIT from real gates |
| **Track record** tab | `[data-evidence="track"]` | Locked `PIT_NOT_VALIDATED`, sample **0**, null win-rate until R16 |
| **Engines used** tab | `[data-evidence="engines"]` | Who votes, who is shadow, who is veto — no engine votes twice |
| Stock decision panels | `.candidate-grid` / `.candidate-card` | BUY **or** SELL **research direction** cards; geometry PENDING unless R5 exists |

**Nothing skipped** means: every required family, source, horizon, and side is a **named slot**. Missing = `UNKNOWN` / `WAIT_*` with a code. Silence is a bug. Stuffing 123 jobs into one score is also a bug.

---

## 0.1 Folder law (do not argue)

| Kind of file | Path | Examples |
|---|---|---|
| Production backend | `D:\TrendForge\backend\trendforge_api\selection\` | `m_factor_bff.py` (new), compose from existing R1–R5/R14 |
| Production API mount | `D:\TrendForge\backend\trendforge_api\main.py` | `GET /api/v1/tools/m_factor` |
| Production frontend | `D:\TrendForge\frontend\` | `m-factor-live.js` (new). Do **not** grow `product-fixture.js` as the live owner |
| Production tests | `D:\TrendForge\backend\tests\` and `D:\TrendForge\frontend\tests\` | `test_m_factor_bff.py`, acceptance IDs |
| Authority docs | this file; File A; `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` §1D | |
| Scratch, failed dumps, one-off notebooks, “try this JSON”, unwanted experiments | `D:\TrendForge\delete\m_factor_wip_YYYY-MM-DD\` | **Never** `backend/tests` for throwaway |
| Temporary pytest sandboxes you will not keep | same `delete\m_factor_wip_*` | After merge, delete the wip folder or leave it under `delete/` |

Do **not** rewrite `r3_live.py` formulas, `resolver.py` FUS-009, `attention_order.py`, `r5_live.py`, or File A. The BFF **consumes** them.

After the build: move unused prompt drafts, curl dumps, and fixture-copy experiments into `D:\TrendForge\delete\m_factor_wip_<date>\`.

---

## 1. Authority (File A wins)

| Rank | File | Use |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` `FUS-009` | Evidence strength, no renormalize, no probability |
| 2 | `AGENTS.md` | Research-only, no broker, HTTP 200 ≠ usable |
| 3 | `docs/fable/FINAL_MERGE_PLAN.md` M-Factor / FMR-010 | long/short = two FUS-009 outputs; class ≠ readiness ≠ state |
| 4 | `docs/DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` §1D | Scanner contract, class bands, BFF rules |
| 5 | `docs/PROFESSIONAL_TRADE_DECISION_MATHEMATICS.md` §14.2–14.3, §15 | Formula crosswalk |
| 6 | `docs/fable/remaining_build/THIRD_EYE_EVIDENCE_RADAR_OPENCODE_PROMPT.md` | How/what/where/when layers; do **not** duplicate a second radar nav |
| 7 | Live code | `r3_live.py` `live_profile()`, `resolver.py`, `r3_claim_adapter.py` |

Conflict: stricter fail-closed / non-probability / no-qty wins.

Hybrid V2 overlay `p̂` / Kelly **must not** be pasted into M-Factor rank. Overlay is a different room (`#hybridV2OverlayPanel`).

---

## 2. Honest live inventory (do not report fixture as runtime)

| Fact | Status 2026-08-22 |
|---|---|
| UI tabs and candidate cards | **Present** (`index.html` 76–88, `product-fixture.js` `renderToolSignals`) |
| Live `app.js` `TOOL_REGISTRY.m_factor` | Ceiling `WAIT_SOURCE_ACTIVATION`; `renderToolRoom` paints WAIT unless fixture owns chrome |
| `window.TrendForgeProductFixture` | **Owns chrome** → user currently sees **ILLUSTRATIVE FIXTURE** TATASTEEL 72/18, fake entry 168.9 |
| `GET /api/v1/tools/m_factor` | **Missing** |
| `GET /api/v1/selection/resolution` | Live R3 FUS-009, `state_ceiling=WAIT`, `entry/target/stop/quantity=null`, cannot CONFIRMED |
| R3 data mode | **`EOD_RESEARCH` only** |
| R3 required source | `nse_bhavcopy_eod` |
| R3 weights | STRUCTURE 0.30, PARTICIPATION 0.25, SAFETY 0.20, MARKET/SECTOR 0.15, EVENT/SPONSOR 0.10 |
| Track record | `PIT_NOT_VALIDATED`, 0 samples |
| Source activation | **false** |

Eyebrow text “INTRADAY F&O RANKING” is **product intent**. Live R3 is **EOD diagnostic**. The BFF must show that split per horizon — not hide it.

---

## 3. The only calculation (no second brain)

```text
long_strength  = FUS-009 evidence_strength(BULLISH hypothesis)
short_strength = FUS-009 evidence_strength(BEARISH hypothesis)
m_balance      = long_strength - short_strength
rank_strength  = max(long_strength, short_strength)

FUS-009:
  support_g = max(eligible supporting claims in correlation group g)
  oppose_g  = max(eligible opposing claims in group g)
  S_f = max(group supports in family f)
  O_f = max(group oppositions in family f)
  support_strength    = 100 * sum(w_f * S_f)
  opposition_strength = 100 * sum(w_f * O_f)
  evidence_strength   = clamp(support_strength - opposition_strength, 0, 100)
```

Missing family stays **0**. Do not renormalize. Correlated OI/volume/transport: **one representative**. PK pipe (`FUS-010`): **zero votes**. Options: at most **one** OPTIONS package.

`M_FACTOR_CLASS_V0` (uncalibrated until R16):

| m_balance | directional_class |
|---|---|
| ≥ +60 | Strong Bull |
| +20 … +59.99 | Bull |
| −19.99 … +19.99 | Neutral |
| −59.99 … −20 | Bear |
| ≤ −60 | Strong Bear |

**Separate forever:** `directional_class` ≠ `readiness_tag` ≠ `public_state`.  
Strong Bull + SETUP_READY + WAIT = bull_wait.

Rank order: `rank_strength` desc, completeness desc, freshness desc, symbol asc.

---

## 4. Four horizons × BUY and SELL (how / what / where / when)

Build **eight boards**, not one soup. A name may appear on **at most one side per horizon**. Conflict → WAIT, not dual seat.

| Horizon | `data_mode` / profile | WHERE | WHEN it may rank | BUY means | SELL means | If data missing |
|---|---|---|---|---|---|---|
| **intra** | Verified **live/intraday** F&O bars + session calendar | NSE F&O equity | During/after IST cash session; unclosed bar cannot lock SETUP_READY | Long hypothesis wins **and** closed/qualifying intra structure | Short hypothesis wins same | `WAIT_HORIZON_INTRADAY_NOT_ACTIVATED` — **do not** fake ORB from EOD |
| **swing** | `EOD_RESEARCH` + official delivery cadence | NSE EQ / F&O | After EOD available_at; delivery never votes as intra | Closed multi-day structure + participation | Same, bearish | R3 live path **this is the only horizon that can show real FUS-009 numbers today** |
| **position** | Weekly/multi-week + SHP/pledge + delayed AMFI as **delayed context** | Nifty-500-like positional universe | AMFI/SHP lag must be labelled delayed | Multi-week constructive + ownership not vetoing | Repair / distribution evidence | `WAIT_HORIZON_POSITION_NOT_WIRED` until weekly structure exists |
| **commodity** | MCX local master + local price/OI | MCX contract, not NSE cash symbol | Local session | Local structure + local OI package | Same, short | CFTC/EIA/WGC/FX = **context only**. Missing local master → **no commodity board row** |

### How / what / where / when (every card, every row)

Every Stock decision panel **must** answer these four, or the card is WAIT:

| Question | Owner | Fail-closed if unanswered |
|---|---|---|
| **HOW** is price moving? | STRUCTURE (closed-bar R5 / intra rule) | No “structure ready” |
| **WHAT** happened? | EVENT / CA / gap / result | Do not invent a catalyst |
| **WHERE** is the instrument? | R4 pin, F&O eligibility, MCX contract, horizon | Unresolved identity → no board |
| **WHEN** was it known? | `available_at`, data_date, session phase, next proof | Mix runs → 503 `WAIT_MIXED_SNAPSHOT` |

Plus File A radar: **SAFE?** (ban/ASM/GSM/MWPL/WAIT_CA) — hard veto beats any rank.

Commander walk (do not score-then-sort):

```text
L0 CLOCK+IDENTITY → L1 SAFETY VETO → L2 DATA MODE (horizon legal?)
→ L3 STRUCTURE HOW → L4 PARTICIPATION (one cash root; delivery second family, EOD only)
→ L5 MARKET/SECTOR context → L6 DERIVATIVES one package → L7 EVENT
→ L8 DELAYED SPONSOR (swing/position only) → L9 MCX LOCAL → L10 GLOBAL COMMODITY context
→ L11 RISK warning qty=0 → L12 FUS-009 fuse → L13 explain how/what/where/when
→ L14 eight boards
```

---

## 5. Paint the five UI surfaces (do not invent a sixth)

### 5.1 Signals (`data-evidence="signals"`)

1. **Market strip** (required by §1D): market condition, adv/dec, average move, bull/bear class counts, IST cutoff, `run_id`, `snapshot_bundle_id`, profile, ceiling. Counts are **not** market probability.
2. **Evidence contribution bars:** long_strength, short_strength, completeness, freshness — from the **selected row’s** FUS-009, not fixture 72/18.
3. **Rank table columns:** symbol, directional_class, long/short, m_balance, readiness_tag, public_state, next proof. Toggleable later: RVol, OI code, delivery % (swing), safety.
4. **Stock decision panels** (`.candidate-card`):  
   - `direction` = BUY if long_strength > short_strength **and** class is Bull/Strong Bull **and** not Neutral; SELL symmetrically. Neutral → no BUY/SELL chip, or `UNRESOLVED`.  
   - Footer **must** say `Research direction only — not an order`.  
   - **Levels:** if R5 geometry missing → `PENDING` / `UNKNOWN` / `NONE — R5 research, not a trade`. **Never** copy fixture 168.9 / 175.2 / 165.1.  
   - Tags only from typed claims (structure, RVol, PK **shadow**, sector, named deal). PK cannot change rank or state.  
   - Checks map to How-validated layers.

Horizon switcher: add **inside** `#tool` hero or Signals toolbar: `intra | swing | position | commodity`. Default **swing** until intra profile is activated. Changing horizon **must not** mix snapshots.

### 5.2 How validated (`data-evidence="validation"`)

Keep the six layers already in `renderToolValidation`. Fill from **gates**, not from pretty copy:

1. Chart structure — R5 / closed-bar  
2. Volume / participation — one activity root  
3. Breakout/breakdown strength — closed only  
4. Market context — index/sector; INDEX_CONFLICT  
5. Multi-timeframe — horizon conflict → WAIT  
6. Safety — activation, surveillance, freshness, CA  

Any hard fail → WAIT/REJECT. Do not show PASS on a layer whose source is STALE.

### 5.3 Track record (`data-evidence="track"`)

**Lock it.** `PIT_NOT_VALIDATED`. give sampleCount, winRate, benchmarkDelta.  
Do **not** compute a fake win % from journal doodles. R16 owns unlock.

### 5.4 Engines used (`data-evidence="engines"`)

Table, not a mystery:

| Engine | Role | Family | Authority |
|---|---|---|---|
| Canonical resolver | Selected/suppressed claims | FUS-009 | **ONLY RANK OWNER** |
| Structure | Closed-bar direction | STRUCTURE | DIRECTION OWNER |
| Participation | One activity root + EOD delivery | PARTICIPATION | ATTENTION |
| Context | Sector/index | MARKET_AND_SECTOR | WEAKEN / WAIT |
| Safety | Ban/CA/activation/freshness | TRADABILITY | **HARD VETO / STATE CEILING** |
| PK shadow | Pipe tags | EXPERIMENTAL / shadow | **NO VOTE** |
| Options/OI | One package | OPTIONS | SUPPORT / OBSTACLE / UNKNOWN |
| Hybrid overlay p̂ | Paper overlay | — | **NOT AN M-FACTOR INPUT** |

### 5.5 Hero / `#toolState`

Replace fixture chips. Live `#toolState` = actual ceiling (`WAIT_SOURCE_ACTIVATION` or `WAIT_HORIZON_*` or `WATCH/WAIT` research). Show real `run_id` and `available_at`. If R3 503, show **`detail.code`** (`R3_RESOLUTION_NOT_READY`, `WAIT_HYBRID_*` analog). Never a blank WAIT.

---

## 6. BFF contract

```text
GET /api/v1/tools/m_factor?horizon=swing&side=both&limit=40&debug=0
```

- `horizon`: `intra|swing|position|commodity` (default `swing`)
- `side`: `buy|sell|both` (filter boards; calculation still runs both hypotheses)
- Read-only. No POST that writes rank. Cannot set `sourceActivationReady`.
- 503 on hash mismatch / mixed R1–R5/R14. Body `{ "code": "WAIT_*", "message": "..." }`.
- Debug=1: selected/suppressed claim IDs, family S_f/O_f, weights, formula version — **must equal** `GET /api/v1/selection/resolution` for the same symbol on swing/EOD.

DTO sketch (camelCase aliases, frozen, no CONFIRMED):

```text
MFactorBatchV1
  schemaVersion, profileId, profileVersion, horizon, dataMode
  runId, snapshotBundleId, r1BundleHash, r2RunHash, r3RunHash
  tradingDate, availableAt, stateCeiling, sourceActivationReady=false
  canUnlockConfirmed=false, calibration="UNCALIBRATED_M_FACTOR_CLASS_V0"
  marketStrip { condition, advancers, decliners, universeSize, cutoffIst }
  longFormula, shortFormula, classVersion
  buyRows[], sellRows[], waitRows[]
  warnings[]  # must include evidence-not-probability

MFactorRowV1
  symbol, instrumentId, horizon
  longStrength, shortStrength, mBalance, rankStrength
  directionalClass, readinessTag, publicState
  how, what, where, when, nextProof, whyWait[]
  completeness, freshness
  entry, stop, t1, t2, quantity   # all null unless R5 geometry exists; still not CONFIRMED
  selectedSupportClaimIds[], selectedOppositionClaimIds[], suppressed[]
  indexConflict: bool
```

Acceptance (must have tests in `backend/tests/test_m_factor_bff.py`):

1. long/short **exactly** equal two FUS-009 hypothesis outputs (FMR-010.1).  
2. Duplicate activity/OI/mirror **cannot** raise rank.  
3. Class, readiness, public_state cannot substitute.  
4. Strong Bull + hard gate remains WAIT/REJECT.  
5. Intra horizon without live bars → WAIT code, **empty buy/sell boards**, not EOD dressed as ORB.  
6. Commodity without MCX local → empty commodity boards; CFTC cannot mint a row.  
7. Track DTO sampleCount==0.  
8. POST `/api/v1/tools/m_factor` → 405.  
9. Mixed hashes → 503 with code.  
10. Fixture HTML values (168.9, FIXTURE-20260729-1042) **must not** appear in live DTO.

Frontend tests: `frontend/tests/acceptance-check.js` — live `m-factor-live.js` must **not** fall back to `decisionTools.m_factor` fixture cards when the BFF returns 200 or 503.

---

## 7. Implementation sequence (small slices; each slice shippable)

1. **BFF swing-only** from hash-matched R3 + R2 + R1. Eight-board fields for other horizons = empty + WAIT codes. Tests first.  
2. **`m-factor-live.js`**: if BFF 200, own `#toolContent` for `m_factor` and the four tabs; if 503, print `detail.code`. Stop painting fixture cards for this tool.  
3. **Stock decision panels** from DTO; geometry null → PENDING.  
4. **How validated + Engines** from gates/engine table.  
5. **Track record lock** (already designed — keep locked).  
6. **Horizon switcher** + fail-closed intra/position/commodity.  
7. Only then: intra profile **if** a verified live bar source exists (DAT-021). Do not pretend.

Do not start with ML, Kelly, overlay p̂, or OpenAlgo.

---

## 8. What a trader is allowed to do after this ships

**Allowed:** pick names for inspection; see why long vs short evidence; see the exact missing proof; switch horizon and see honest WAIT.

**Forbidden (UI and API must make this true):** treat 72 as 72% win; size from rank; buy fixture levels; use delayed AMFI as “bought today”; seat the same name BUY and SELL on one horizon; report Track record as performance.

`qty` stays 0. Broker stays unreachable.

---

## 9. Stop-if

Stop and report instead of guessing if:

- You would set `can_unlock_confirmed=true` or emit CONFIRMED.  
- You would mix R1/R2/R3/R5 hashes.  
- You would use EOD delivery or AMFI on the **intra** board.  
- You would put CFTC/WGC names on the **commodity** board without MCX local.  
- You would write experiments into `backend/` instead of `delete/m_factor_wip_*`.  
- You would leave fixture TATASTEEL 72/18 as the live Signals view after BFF exists.

---

## 10. Done when

- Discovery → M opens **live** Signals / How validated / Track record / Engines used.  
- Stock decision panels render from BFF, BUY and SELL, levels PENDING without R5.  
- Four horizon tabs exist; only legal horizons have rows.  
- `GET /api/v1/tools/m_factor` documented and tested.  
- Fixture is labelled fixture or gone from this tool.  
- Throwaway files live only under `D:\TrendForge\delete\m_factor_wip_*`.  
- No new Combined_Score. No win %. No CONFIRMED.
