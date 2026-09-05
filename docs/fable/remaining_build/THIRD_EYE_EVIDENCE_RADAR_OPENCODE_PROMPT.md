# OPENCODE BUILD PROMPT — 3rd-eye evidence radar
## All inventory as typed slots · four horizons · BUY and SELL · how / what / where / when

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. Shell: PowerShell. Chain with `;` not `&&`.

Copy this **entire file**. Think first. If a source cannot name a stock, do not print a stock-level fact. If a source is unused, it must appear as a named UNKNOWN slot — **silence is a bug**.

---

## 0. What this is (and the lie it forbids)

You are **not** building a smarter sort of the current top-10.

Live `selection/top10_research.py` is a **WATCH-40 sticker sort**:
`display_score = R2 attention_priority + capped stickers (gap 0.02, named deal 0.05, MF 0.04, cap 0.10)`, split by `evidence_direction`, take 10+10. Delivery is shown not scored. SHP FII is always null. Market FII is a chip. That is a shortlist. It is **not** 3rd-eye.

You **are** building a **research evidence radar**:

1. Read **every** live R1 source contract (today **123 jobs**) plus companions (index close, aliases, last-good).
2. For every contract, fill a **typed slot** (PRESENT / VALID_EMPTY / STALE / WRONG_GRAIN / BLOCKED / UNPROVEN / NOT_NORMALIZED / COMPANION_ONLY / NOT_APPLICABLE_TO_HORIZON).
3. Answer **how / what / where / when** per instrument × horizon.
4. Emit **BUY and SELL research boards** for **intraday, swing, position, commodity**.
5. Fuse with File A **FUS-009** (one representative per family / correlation group). **Never** turn 140 links, 165 cards, or 123 jobs into 123 votes.

**The user asked to use all ~140 links and skip nothing.**  
Correct reading: **use every link as evidence of a typed job.**  
Wrong reading: **add every link into a score.** That is the bug File A was written to kill.

Public state stays **WATCH / WAIT / REJECT**. **0 CONFIRMED. qty=0. no broker.**  
Do **not** set `sourceActivationReady=true`. Do **not** rebuild R1–R5 or R14.

---

## 1. Commander order — how a high-intelligence desk actually uses this data

This is the **best order**. Do not “score everything then sort.” Walk the layers. A later layer cannot rescue a failed earlier layer.

```text
L0  CLOCK + IDENTITY     J01   IST session, calendar, ISIN/instrument_id (R4 pin)
L1  SAFETY VETO          J02   ban / ASM / GSM / WAIT_CA / circuit / MWPL-missing
L2  DATA MODE            DAT-002  EOD closed vs live-unverified vs delayed
L3  STRUCTURE (HOW price)     R5 closed-bar tags from adjusted series + R14 CA
L4  PARTICIPATION (HOW money) one cash root: R2 return+activity is ONE story
                              delivery is a SECOND family (EOD only)
L5  MARKET / SECTOR      J05   index/breadth/VIX/sector = context, not a stock vote
L6  DERIVATIVES PACKAGE  J06/J07  OI/basis one family; options one family; missing ≠ punish cash
L7  EVENT / SPONSOR      J08/J09  named deal / filing / CA — dataset-root once
L8  DELAYED SPONSOR      J10   AMFI / SHP — swing + position only; never “bought today”
L9  MCX LOCAL            J11   commodity boards require local master + local price/OI
L10 GLOBAL COMMODITY     J12   CFTC/EIA/WGC/FX — context; cannot replace L9
L11 RISK WARNING ONLY    J13   research warning; qty stays 0
L12 FUSE                 FUS-009  max per family, cap, contradiction; not a Combined_Score
L13 EXPLAIN              how / what / where / when + File A eight radar questions
L14 BOARD                BUY/SELL × 4 horizons; WAIT; fewer than 10 is honest
```

**Hard sequencing rules**

| If this fails | You may not |
|---|---|
| L0 identity unresolved | Rank, board, or invent a symbol |
| L1 hard veto (REJECT, WAIT_CA, F&O ban for F&O rows) | Put the name on any BUY/SELL board |
| L2 horizon data_mode illegal | Use that horizon’s board (intra without verified live bars → WAIT ceiling, not fake ORB) |
| L3 no closed bar / CA break | Claim “structure ready” |
| L4 volume already in R2 | Add volume again as a second vote |
| L8 delayed AMFI | Label “FII/MF bought today” or use on **intraday** board |
| L9 MCX master/local missing | Put a name on the **commodity** board from CFTC/WGC |
| L12 family conflict above profile | Seat the name on BUY **and** SELL of the same horizon |

Causal chain the radar must speak (plain trader English, File A families under the hood):

```text
WHAT happened?     event / CA / gap / result          EVENT_AND_SPONSOR or STRUCTURE
WHO is in it?      named deal / delayed MF / delivery  EVENT or SPONSOR_DELAYED or PARTICIPATION
HOW is it moving?  closed structure + one activity root STRUCTURE + PARTICIPATION
WHERE is it?       NSE cash / F&O / MCX contract + horizon
WHEN was it known? available_at, freshness, session phase, next trigger, invalidation
SAFE?              J02 tradability — veto or WAIT
```

If the chain cannot be spoken with evidence, the row is **WAIT with whyUnknown**, not a confident BUY.

---

## 2. Authority (File A wins)

| Rank | File | Use |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` | Sequence, four states, FUS-009 families, PRF-001…007, eight radar questions §13.1, no qty |
| 2 | `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` | Do not rebuild live R1–R5/R14. 123 jobs. Companions ≠ extra jobs. Workbench is glass |
| 3 | `docs/fable/FINAL_MERGE_PLAN.md` | Paint **All Stocks / Live Ops**, not `/inventory-workbench` |
| 4 | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | J01–J14 jobs, named deals, AMFI lag. **No** File B qty / OpenAlgo |
| 5 | `backend/trendforge_api/source_inventory_compiler.py` `DECISION_JOB_SPECS` | Live J01–J14 text |
| 6 | `TREND_FORGE_SOURCE_REGISTRY.md` | Source meaning. HTTP 200 ≠ usable |

Overlay V3 S4/S5/Kelly: **do not paste** into this radar or into `r5_live.py`.

R6 stickers + current top10 **stay**. This radar **supersedes them as the intelligence layer** and may feed better boards. Do not delete `r6_live.py` / `top10_research.py`.

---

## 3. Honest counts (memorize — tests will catch the lie)

| Number | What it is | What it is **not** |
|---|---|---|
| ~165 inventory **cards** | Gallery / workbook rows | 165 votes |
| ~129 historical unique keys | Old map | Today’s live job count |
| **123** live R1 `source_key` contracts | Jobs in `InventorySourceBundleV1` | 123 independent confirmations |
| Aliases / mirrors / BSE copies | Same dataset-root | Extra family votes |
| Index close (A5) | **Companion** to cash | 124th job |
| PK digest (R4) | Inventory pin | A vote |
| `nse_fii_dii` | **Market** net FII/DII | Per-stock “FII bought RELIANCE” |
| HTTP 200 / last-good | Transport or stale artifact | Fresh structured fact |
| Current top-10 | Display ranks on WATCH-40 | Universe 3rd-eye |

**Nothing skipped** means:

```text
len(radar.coverage.sourceKeys) == len(latest R1 source_records)
every source_key has exactly one SlotStatus
companions listed separately, never mixed into job count
if you did not calculate a number, status is NOT_NORMALIZED or NOT_APPLICABLE, never omitted
```

If OpenCode “skips hard sources because parsers are ugly,” the ticket **fails**.

---

## 4. Already live — READ, do not rewrite

```
selection/inventory_source_bundle.py     R1  123 jobs + stock rows
selection/attention_order.py             R2-A  priority = 0.5*returnPct + 0.5*max(volPct,turnoverPct)
selection/r3_live.py                     WAIT fuse, one FTR-040 participation claim
selection/r4_live.py                     instrument_id pin; PK zero-vote
selection/r14_live.py                    CA join DAT-022
selection/r5_live.py                     WAIT tags; no live T1/T2 CONFIRMED
selection/r6_live.py                     WATCH-40 stickers (keep)
selection/top10_research.py              simple 10+10 (keep; radar feeds a NEW board)
selection/r2b_live.py                    named activation WAIT; sourceActivationReady=false
selection/fo_a6_enrichment.py            F&O OI package on WATCH
selection/mcx_contracts.py               MCX master gates (WAIT without local)
selection/index_a5_context.py            index companion
selection/series_layers.py               adjusted series; never mutate RAW
source_inventory_compiler.py             J01–J14 + maturity ladder
fii_stock_signals.py                     named deals + third-party INFO pills
evidence_builder.py                      nse_large_deals, amfi_stock_deltas
hybrid_v2/                               paper overlay; do not fuse into radar score
```

R2 field names (map, **do not rename** on `AttentionRowV1`):

| Python | JSON |
|---|---|
| `evidence_direction` | `evidenceDirection` |
| `public_state` | `publicState` |
| `attention_priority` | `attentionPriority` |

SHP FII% vs prior quarter is **still not a live parser**. Default `shpFiiDelta=null` + `SHP_FII_DELTA_NOT_NORMALIZED`. Promoter/public % may be shown as delayed ownership **context**, never as FII flow.

---

## 5. How / what / where / when (the product sentence)

Every **horizon row** (instrument × profile) MUST fill this DTO. Empty string is forbidden; use UNKNOWN + code.

```text
how     HOW is the market expressing the idea?
        structure tag + one participation story + OI package if F&O
        example: "EOD close accepted above prior high; delivery z unknown; FO OI LONG_BUILD"

what    WHAT evidence exists / what changed / what event?
        R5 tags, named deal, CA, gap, AMFI delta, market FII chip
        example: "Named bulk BUY client=… dated T-1; AMFI +qty month=2026-06 DELAYED"

where   WHERE is this idea located?
        market (NSE_CASH | NSE_FO | MCX) + horizon + (optional) structure location label from R5
        NOT live T1/T2 as trades. Location may be "above prior high" / "inside NR7" / "NEAR_TENDER"
        example: "NSE_CASH swing; setup=BREAKOUT_TAG; not a trade entry"

when    WHEN was it knowable, and what happens next?
        available_at, source freshness, IST session phase, nextConfirmCondition, invalidationCondition
        example: "known after 15:35 IST EOD file; next=independent family still missing; invalid=close back inside range"
```

Plus File A **eight radar questions** (§13.1) on the same row:

1. instrument / profile / timeframe  
2. four-state classification (WATCH/WAIT/REJECT only here)  
3. why it entered now  
4. which independent **families** support  
5. strongest contradiction or veto  
6. missing proof + exact condition that changes state  
7. completeness / freshness of the run  
8. what changed vs comparable prior run (`NO_BASELINE` if none)

Plus the four practical trader questions (historical screener purpose — still valid as copy, not as extra votes):

1. Why is it moving?  
2. Who is behind it?  
3. Is structure ready?  
4. Is money moving **in this horizon’s legal clock**?

`CONFIRMED` / qty / “is expected reward enough” / Kelly stay **unanswered as numbers**. Put `NOT_IN_SCOPE_RESEARCH_RADAR` in whyUnknown for those.

---

## 6. Four horizons — honest File A mapping

File A primary horizons are **intraday and swing**. MCX has its own profiles. **Position** is a **research overlay profile**, not a silent File A CONFIRMED path. Name it honestly.

| Board horizon | File A profile(s) | Legal data_mode | Ceiling this ticket | Must use | Must NOT use as proof |
|---|---|---|---|---|---|
| `INTRADAY` | PRF-001 continuation, PRF-002 reversal | verified live/closed intraday bars | **WAIT** until live bar contract exists (`W-002` / `DAT-002`). May still **rank research attention** from official activity + pre-open last-good, labelled `DATA_MODE_EOD_OR_UNVERIFIED` | J04 pre-open if window; J03 session activity as **discovery**; R2 cash as **same-root** | Delivery (`REJ-004`); AMFI “today” (`T-037`); CFTC; SHP quarter; ORB/VWAP as CONFIRMED (`FTR-010` stays WAIT) |
| `SWING` | PRF-003 continuation, PRF-004 event | official EOD adjusted closed bars | WAIT (no CONFIRMED unlock) | R5 tags, R14 CA, delivery z if ≥20 PIT, named deals, A6 FO package, market FII chip | Intraday delivery; aggregate FII as stock actor (`PRF-004`) |
| `POSITION` | **New** `PRF-RESEARCH-POSITION-WAIT` | EOD + delayed J10 | WAIT | Multi-week RS vs index (FTR-004 horizons), AMFI delta labelled DELAYED, SHP promoter/public, results `available_at` | Session volume as “accumulation today”; SHP date as last week; `nse_fii_dii` per name |
| `COMMODITY` | PRF-005 metals, PRF-006 energy, PRF-007 base/agri | **local MCX** master + local OHLCV/OI | WAIT without local artifact (`FTR-028`) | J11 local; DTE/tender/delivery windows; J12 as **grey context** | CFTC/WGC/EIA as local confirm (`FTR-030`); NSE cash RS as MCX proof |

**BUY vs SELL** is a **board**, not `public_state`.  
Direction for a horizon comes from **that horizon’s fused families**, not blindly from R2 `evidence_direction` (R2 is cash session attention — correct for swing discovery, often **wrong** for position/commodity).

Rules:

- `INTRADAY` / `SWING` cash: start from R2 `evidence_direction`, then **allow** delayed/event families to mark `CONFLICT` (row drops off both boards, stays on inspector).
- `POSITION`: direction from delayed sponsor + multi-week RS; if they fight session R2, **do not** force the swing board direction onto position.
- `COMMODITY`: direction from **local** MCX structure/OI; global COT sign is context.
- Hard veto still drops every board.

If a horizon has fewer than 10 honest names, return what exists. **No third-party backfill.**

---

## 7. Slot catalog — every source is a job, not a vote

Build `selection/evidence_radar/slot_catalog.py` from **live R1 + compiler**, not a handwritten 140-row hallucination.

For each R1 `source_key`:

```text
sourceKey
canonicalRoot          (normalized_source_key / dataset_root)
decisionJobs[]         J01–J14 from compiler (empty → cannot vote, still a slot)
evidenceFamily         File A §11.1 or UNKNOWN_FAMILY
correlationGroup       CG_* or ROOT:<canonical>
grain                  SYMBOL | MARKET | SECTOR | CONTRACT | MACRO | COMPANION
horizonsAllowed[]      INTRADAY | SWING | POSITION | COMMODITY
canSupportConfirmed    must be false this ticket
authority              OFFICIAL | DELAYED_OFFICIAL | CALCULATED | SECONDARY | UNOFFICIAL
calculate              formula id or NOT_NORMALIZED
wrongGrainIfCopiedToSymbol  bool  (true for nse_fii_dii, CFTC, VIX, etc.)
```

**Calculate** means: if the source **can** produce a number for this grain, compute it with PIT, formula version, and null-reason. Do not skip.

Minimum **required calculate recipes** (use last-good; never invent):

| Family / source class | Formula (research, versioned) | Null / refuse |
|---|---|---|
| Cash session (already R2) | `attention = 0.5*retPct + 0.5*max(volPct,toPct)` — **do not recompute a second cash vote**; **read** R2 | Stale/unknown rows already unranked |
| Gap (adjusted, R14) | `(open - prevClose) / prevClose` if not WAIT_CA | WAIT_CA → UNKNOWN; never RAW unadjusted if CA pending |
| Delivery (MTO) | z vs PIT rolling ≥20 completed sessions (`FTR-019`) | <20, missing, or **intraday board** → UNKNOWN / FORBIDDEN |
| Pre-open (`FTR-001`) | `gap_pct` from IEP vs prevClose; imbalance = (buy−sell)/eligible | Outside window or no snapshots → not reusable as live |
| RS (`FTR-004`) | `stock_ret - benchmark_ret` over versioned 5d / 21d / 63d windows, percentile in PIT universe | Misaligned dates / CA incomplete |
| Named deal | side + client string as-is; FII/FPI in client → `NAMED_FII_LIKE_DEAL` still EVENT | Empty client → `UNNAMED_DEAL` ≠ FII |
| AMFI | period delta, `DELAYED_MF`, month stamp | Never “today” |
| SHP | promoter/public if parsed; `shpFiiDelta=null` | Do not invent FII% |
| Market FII | `MARKET_FII_NET` chip only | Never copy onto a symbol as bought/sold |
| FO A6 | OI quadrant **package** | Cash-only not punished |
| Options J07 | `OPTIONS_PACKAGE=UNKNOWN_NEEDS_R12` unless a **fresh expiry-scoped** chain exists | PCR static ≠ direction (`REJ-006`) |
| MCX local | close/OI change vs prior local bar; DTE from master | Global gold cannot substitute |
| CFTC/EIA/WGC | standardized delayed z by commodity profile | Cannot create local OI |
| Third-party FII screens | INFO pill, score +0 | Cannot enter a board alone |
| MWPL % | still unproven | Ban CSV ≠ MWPL %; confirm-ineligible |
| Surveillance / pledge / ASM/GSM | veto or warning slots | Metadata-only ≠ sponsor proof |
| PK scanners | shadow / digest only | Zero vote (`CG_PK_SHADOW_NATIVE`) |

Reuse existing parsers under `backend/trendforge_api/parsers/`. If a parser exists but is not wired into the radar, **wire it**. If last-good exists but schema is pending, slot = `NOT_NORMALIZED` with the registry reason — **still counted, not skipped**.

---

## 8. Fusion — 3rd eye without vote inflation

Per horizon, run File A §11.2 **inside this package**, WAIT-only:

```text
for each family:
  eligible = fresh, authority-allowed, horizon-legal claims
  representative = highest quality-adjusted per correlation group
  family_base = max(representatives)
  corroboration = epsilon * bounded extra independent groups   # epsilon may be 0 (R3 live used 0)
  family_score = cap(family_base + corroboration) * contradiction_penalty
required family missing → that family is 0 and state cannot be CONFIRMED (already true)
```

Then **displayRankKey** (research only, never labelled probability):

```text
displayRankKey = versioned weighted family_score
                 AFTER hard veto
                 AFTER horizon legality
                 NOT a Combined_Score
                 NOT File A public_state
```

Caps you must encode as tests:

- `CG_ACTIVITY_SESSION`: volume gainer + most-active + RVOL + R2 cash activity → **one** participation story  
- `CG_EVENT_ROOT`: NSE deal + BSE mirror of same deal → **one** event  
- `CG_FUTURES_OI`: OI level/change/quadrant/basis → **one** derivatives package  
- `CG_OPTION_CHAIN`: PCR/walls/max pain/IV → **one** options package  
- `CG_PRICE_STRUCTURE`: breakout + new high from same bars → **one** structure unless profile proves distinct horizons  
- Market FII + stock named deal are **different grains**; market FII **must not** add to the stock’s EVENT family  
- Delivery and volume are **not** two votes from the same print; delivery is EOD MTO, volume is session activity  

R3 already emits one FTR-040 participation claim. **Do not emit a second.** Radar **reads** R3/R5 claims and **adds** only families R3 left non-directional (events, delayed sponsor, MCX, options-as-unknown).

---

## 9. Two-stage universe (so “all stocks” is real, and you do not melt the box)

**Stage A — slot fill (nothing skipped), all resolved instruments + all MCX contracts in master**

Join last-good by grain. Cheap. Output: coverage matrix + per-row slot map. Persist hash.

**Stage B — deep calculate + fuse + boards**

- Cash horizons: start from R2 attention queue (WATCH first), deep-calc **at least** top 200 WATCH + any name with a **named official event** even if not top 200 (so a block deal on a quiet name is not skipped).
- Position: same 200 + AMFI/SHP hits with non-null delayed delta.
- Commodity: **all** MCX contracts that have master + local bar; if local missing, row exists as WAIT with L9 UNKNOWN, **not deleted**.

Boards: 10 BUY + 10 SELL **per horizon** (8 lists). Fewer is OK.

This is how you use **all links** without pretending 2,463 × 123 numeric features must all be hot on every GET.

GET may compute-on-read from latest spine (preferred, like s4s5) **or** persist `PRF-EVIDENCE-RADAR-WAIT`. Never flip activation.

---

## 10. What to build

**Backend package** (new tree; do not stuff this into `r5_live.py` or `top10_research.py`):

```
backend/trendforge_api/selection/evidence_radar/
  __init__.py
  catalog.py          # slot catalog from live R1 + compiler
  slots.py            # Stage A fill
  calculate.py        # Stage B formulas (null-reasons mandatory)
  fuse.py             # FUS-009 per horizon, WAIT
  explain.py          # how/what/where/when + eight questions
  boards.py           # 4 horizons × BUY/SELL
  coverage.py         # nothing-skipped report
```

Routes:

- `GET /api/v1/selection/evidence-radar/coverage`  — source_key completeness  
- `GET /api/v1/selection/evidence-radar`           — dossiers + boards  
- `GET /api/v1/selection/evidence-radar/boards?horizon=SWING`  
- POST → **405**

Query `horizon` ∈ `INTRADAY|SWING|POSITION|COMMODITY|ALL`. Default ALL.

**Row DTO (camelCase)** — keep WAIT locks in validators like R5/R6:

```
symbol, instrumentId, market, horizon,
publicState,          # from R2/R14/MCX gates; never CONFIRMED
researchBoard,        # BUY | SELL | NONE
displayRank,
families: { name: { status, direction, representativeClaimId, why } },
slotsSkippedCount,    # must be 0; use unknownCount instead
unknownCount,
how, what, where, when,
why[], whyUnknown[],
nextConfirmCondition, invalidationCondition,
whatChanged,          # or NO_BASELINE
freshness, completeness,
dataMode,
marketFiiChip,        # board-level, not per symbol
canUnlockConfirmed=false,
sourceActivationReady=false,
calibration=RESEARCH_RADAR_NOT_CONFIRMED
```

**Frontend (one shell)**

Paint existing All Stocks / Live Ops. Do **not** create a second app or a second S0–S9 File A strip.

- `#evidenceRadarPanel` with horizon tabs: Intra / Swing / Position / Commodity  
- Each tab: BUY 10 | SELL 10 cards showing **how/what/where/when** + UNKNOWN chips  
- Coverage strip: `123/123 slots represented` (or live count) + list of NOT_NORMALIZED keys  
- Inspector: reuse family supports / contradiction; do not fill entry/T1 as trades  
- Adapter: GET radar; 503 → empty boards + WAIT copy  
- Files: `frontend/evidence-radar.js`, mounts in `frontend/index.html`, `selection-live-adapter.js`, `acceptance-check.js`, `frontend/styles.css`

If `top10-research.js` exists, **keep it** as the old shortlist; radar is the 3rd eye. Label the old panel `R6 shortlist (stickers)` so the user can see both.

---

## 11. Forbidden (instant fail)

- 165 cards / 140 links / 123 jobs as additive votes  
- `nse_fii_dii` copied onto a symbol as bought/sold  
- Unnamed deal labelled FII  
- Third-party FII screen creating a board seat  
- AMFI or SHP as “last week / today”  
- Delivery on the **intraday** board  
- CFTC/WGC confirming a **commodity** board seat without local MCX  
- Volume added on top of R2 priority  
- Companions counted as extra jobs  
- PK / shadow / Hybrid `p̂` / Kelly as File A state  
- `sourceActivationReady=true`, CONFIRMED rows, qty, broker, live T1/T2 as orders  
- Rebuilding R1–R5/R14 “because the prompt is big”  
- Dual-starting the collector  
- Pasting S4–S9 into `r5_live.py`  
- Silent skip of a source_key  

---

## 12. Tests (must pass; this is the intelligence contract)

| ID | Assert |
|---|---|
| C1 | Coverage: every latest-R1 `source_key` has a slot status; `skippedCount==0` |
| C2 | Aliases/mirrors share `dataset_root`; second URL does not add a family vote |
| C3 | Index close companion is not a 124th job |
| C4 | `nse_fii_dii` cannot set per-symbol `fiiBoughtThisStock` |
| C5 | Unnamed large deal ≠ FII buy |
| C6 | Third-party screen +0; cannot enter boards without R2/MCX identity |
| C7 | AMFI labelled delayed; SHP `shpFiiDelta is None`; never “last week” |
| C8 | Delivery absent from INTRADAY board claims |
| C9 | WAIT_CA / REJECT excluded from all eight boards |
| C10 | Cash-only name not punished for missing FO |
| C11 | Volume not added twice on top of R2 |
| C12 | Commodity board empty-or-WAIT when local MCX missing even if CFTC present |
| C13 | INTRADAY `dataMode` is not `LIVE_VERIFIED` unless a verified bar contract exists; ORB not CONFIRMED |
| C14 | POSITION direction may differ from R2 session direction without rewriting R2 |
| C15 | CONFLICT (structure vs named event) → `researchBoard=NONE`, still in inspector |
| C16 | `canUnlockConfirmed=false`; 0 CONFIRMED; R2 `runHash` unchanged (read-only) |
| C17 | POST 405; lineage mismatch 503 |
| C18 | Eight radar questions all non-empty (UNKNOWN codes allowed) |
| C19 | how/what/where/when all non-empty |
| C20 | Existing `tests/test_r5_live_structure.py`, `test_r14_live_ca_join.py`, `test_r6_live.py`, `test_top10_research.py` still pass |

```
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_evidence_radar.py tests/test_r6_live.py tests/test_top10_research.py tests/test_r5_live_structure.py tests/test_r14_live_ca_join.py tests/test_r2b_live_named_activation.py -q
cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Scratch → `delete/evidence_radar_wip_<date>/`. No `tmp_*.py` in repo root.

---

## 13. Docs (short)

Patch `fileindex.md`, `docs/BUILD_STATUS.md`, `docs/DECISIONS.md` (**D-044**: evidence radar uses all jobs as typed slots; 165≠votes; four horizon WAIT boards; not CONFIRMED), `docs/VALIDATION.md`, remaining_build README.

Do **not** mark R2-B unlock, File A first CONFIRMED, R11 complete, or R12 options live.

---

## 14. Stop

Do not start R5 live T1/T2 as trades, Kelly size, R12 chain trading, OpenAlgo, or `sourceActivationReady=true`.

**Success observed:**

1. Coverage strip shows every live job as a slot (no silent skip).  
2. Four horizon tabs, BUY and SELL, each card speaks how/what/where/when plus UNKNOWN.  
3. A quiet name with a real named official deal can appear even if it was not R2 top-40.  
4. Market FII never becomes “FII bought this stock.”  
5. Commodity tab does not rank gold from CFTC alone.  
6. Public state still has **0 CONFIRMED**.

That is the 3rd eye: **see every source, count it once, say what is missing, do not pretend a stack of websites is a buy.**
