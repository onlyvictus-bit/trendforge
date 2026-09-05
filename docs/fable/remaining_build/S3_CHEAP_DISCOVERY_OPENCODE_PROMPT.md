# OPENCODE BUILD PROMPT — File A S3 cheap discovery
## Full eligible universe, WATCH/WAIT shortlist, completeness — not a second ranker

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. Shell: PowerShell. Chain with `;` not `&&`.

Copy this **entire file**. Think first.

Cash **S1 is usable** (WAIT). **S2 weather DTO is live** (context only). **Do not rebuild S1, S2, R1–R5, R14, R6, or the evidence radar.**  
This ticket finishes **S3 only**: File A `SEL-004` cheap full-universe discovery.

Do **not** set `sourceActivationReady=true`. Do **not** emit CONFIRMED or qty. Do **not** dual-start the collector. **Delivery is forbidden in S3** (swing S5 only).

---

## 0. Outcome (done means this was **observed**)

1. One GET returns a **cheap-discovery batch** over the **full S1-eligible cash universe** (today ~2,463 resolved names, not a 40-name sticker list).
2. Every eligible name has: WATCH or WAIT (or already REJECT from S1), **named discovery tags**, missing-layer UNKNOWN codes, and **no CONFIRMED**.
3. Completeness is visible: scanned / eligible / excluded / failed / unattempted. Partial scan → `WAIT_PARTIAL_SCAN`, never fake 100%.
4. All Stocks / Live Ops shows a **S3 WATCH queue** (bounded display, e.g. top 50 by R2 attention among WATCH) with why-appeared chips. Full universe still persisted/returned, not dropped.
5. Pre-open, most-active, OI spurts, cheap NR, RS, deal/announcement **indices** are **joins**, not extra votes on top of R2 cash attention.

---

## 1. What S3 is (File A wins)

| Stage | ID | Work | Ceiling |
|---|---|---|---|
| **S3** | `SEL-004` | Cheap full-universe discovery: pre-open, activity, RVOL, OI spurts, compression, RS, announcements/deal **indices**, native core scanners | Bounded WATCH/WAIT shortlist; completeness; **pre-R5 WAIT** |

Also File A §25.25.4 / order-3: five cash CSV discovery profiles (already coded as A3). Additive Combined_Score is **REJECTED**.

| This ticket IS | This ticket is NOT |
|---|---|
| Cheap pass **every eligible stock** | R5/S4 closed-bar structure pack |
| Tags + one shortlist + completeness | A second `attention_priority` formula |
| WATCH/WAIT only | CONFIRMED, qty, T1/T2 as trades |
| Delivery **excluded** | Intraday “delivery quality” (`REJ-004` / T-034) |

R2-A already orders attention:  
`priority = 0.5*returnPercentile + 0.5*max(volume,turnover) percentiles`.  
**Do not recompute that. Read it.** S3 **adds discovery reasons** on the same universe.

A3 already emits five profiles (`DISC_EOD_MOMENTUM`, `RECOVERY`, `RANGE`, `LIQUIDITY`, `NARROW_SESSION`) as WATCH reasons only. **Read A3. Do not rewrite it.** S3 **joins** A3 + R2 + extra cheap last-goods.

---

## 2. Authority

| Rank | File | Use |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` | §9 S3 `SEL-004`; §25.25.4 five profiles; §25.25.7 family caps; FTR-001/017/018; no qty |
| 2 | `docs/fable/remaining_build/R0_R1_R2_LOCKED_PLAN_2026-08-15.md` | R2 is attention, not a new S0–S3. A3 is cash discovery. Workbench is glass |
| 3 | `docs/fable/FINAL_MERGE_PLAN.md` | Paint All Stocks / Live Ops, not `/inventory-workbench` |
| 4 | `docs/fable/TRENDFORGE_HYBRID_DATA_TO_DECISION_PLAN_2026-07-17.md` | Detail only. No File B qty |

S2 weather (`GET /api/v1/selection/market-weather`) is **context**. Nifty up must **not** add a discovery vote.

R8 native scanners are **not** built. S3 may **consume** a native registry **if** one exists; otherwise tag `NATIVE_SCANNER_NOT_REGISTERED` and do **not** let PK/workbench `screener.js` vote (`CG_PK_SHADOW_NATIVE`).

---

## 3. Already live — READ, do not rewrite

```
selection/cash_a2_identity.py          S1 identity
selection/cash_a3_discovery.py         five DISC_EOD_* profiles, WATCH only
selection/attention_order.py           R2-A full-universe attention
selection/r14_live.py / r5_live.py     later; S3 must not require R5 to run
selection/s2_market_weather.py         context only, weight 0
selection/r6_live.py / top10_research  shortlist stickers; not S3
selection/evidence_radar/              3rd-eye; do not stuff S3 into boards.py
market_activity.py                     activity endpoints (discovery join)
```

R2 field names (map, **do not rename**): `evidence_direction` → JSON `evidenceDirection`.

---

## 4. Cheap layers (how to use each — one family each)

Commander order: **S1 veto first**, then cheap tags, then display order from **existing R2**. Missing layer = UNKNOWN code, not skip the name.

| Layer | Source | Family / group | Allowed S3 use | Forbidden |
|---|---|---|---|---|
| S1 eligibility | A2 + ban/CA | TRADABILITY | REJECT/WAIT already set; S3 cannot revive REJECT | Rank a banned name |
| A3 five profiles | `latest_cash_discovery()` | STRUCTURE / PARTICIPATION as **reasons** | Copy tags onto the row | New Combined_Score |
| R2 attention | `latest_attention_order()` | `CG_ACTIVITY_SESSION` **one** cash story | Display order only | Add volume again |
| Pre-open `FTR-001` | `nse_preopen` / `nse_preopen_fo` last-good | `CG_PREOPEN` | IEP gap tag if **in window** and last-good exists | Fake ORB; reuse yesterday’s IEP as live; double-count vs Nifty weather |
| Activity `FTR-018` | `nse_most_active_volume/value`, `nse_volume_gainers` | `CG_ACTIVITY_SESSION` | Join flag `ON_MOST_ACTIVE` | Second volume vote |
| RVOL | EOD volume vs PIT median of prior **closed** sessions (A4 bars) | `CG_ACTIVITY_SESSION` | `RVOL_EOD` tag if ≥20 sessions | RVOL-TOD without verified intra bars (`DAT-002` → UNKNOWN) |
| OI spurts | `nse_oi_spurts` / `nse_oi_spurts_contracts` last-good | `CG_FUTURES_OI` **discovery** | F&O names only; cash-only not punished | Options PCR as direction |
| Cheap compression | Same-session range vs universe (A3 `NARROW_SESSION`) + optional NR7 if **≥8 closed bars** | `CG_COMPRESSION` **one** | Tag only; max WATCH | Full VCP/TTM as S3 (that is S4/R5) |
| RS `FTR-004` | Stock vs Nifty 50, versioned 1d/5d if bars align | context attribute | Percentile in PIT eligible only | CA WAIT_CA → no RS |
| Deal/announcement **index** | Official large deals / announcements last-good **symbol list** | `CG_EVENT_ROOT` | Discovery lead `HAS_OFFICIAL_EVENT` | “FII bought X” from `nse_fii_dii`; unnamed deal as FII |
| Native scanners | none registered | — | `NATIVE_SCANNER_NOT_REGISTERED` | PK/workbench as votes |
| Delivery | MTO | — | **Do not query in S3** | Intraday or cheap-discovery delivery |

Same session volume/gainer/most-active/R2 cash = **one** participation story after caps.

---

## 5. Completeness (required)

Against S1 eligible universe (timeouts/unattempted are **not** exclusions):

```text
completeness = scanned_ok / eligible
if completeness < profile.min_completeness:  # versioned, default 0.95
    state_ceiling = WAIT
    gate += WAIT_PARTIAL_SCAN
```

DTO must show: `eligibleCount, scannedCount, excludedCount, failedCount, unattemptedCount, completeness, waitPartialScan`.

A3/R2 lineage mismatch → 503 `WAIT_S3_LINEAGE_MISMATCH`. Do not mix hashes.

---

## 6. What to build

**Backend** (new tree, do not stuff into `attention_order.py` or `r5_live.py`):

```
backend/trendforge_api/selection/s3_cheap_discovery.py
backend/tests/test_s3_cheap_discovery.py
```

`build_s3_cheap_discovery()`:

1. Load latest A2/A3 + R2 (hash-match).
2. Load last-good for pre-open, activity, OI spurts, deals/announcements **once**.
3. For each A3/R2 row: attach tags; skip delivery; cash-only missing FO = not a penalty.
4. `publicState` stays R2/A3 WATCH/WAIT/REJECT. Discovery tags cannot upgrade WAIT_CA or REJECT.
5. `researchQueue=WATCH` names sorted by **existing** R2 `attentionPriority` (stable). Cap **display** e.g. 50; full rows still in payload or a paged `?limit=`.

Ceiling: `LIVE_S3_WATCH_WAIT_ONLY`. Validators: `canUnlockConfirmed=false`, `sourceActivationReady=false`, `confirmedCount=0`.

Routes:

- `GET /api/v1/selection/cheap-discovery`
- `GET /api/v1/selection/cheap-discovery/watch?limit=50`
- POST → **405**

Prefer GET from latest spine (like S2). Persist only if tests need it: profile `PRF-S3-CHEAP-WAIT`.

**Row DTO (camelCase):**

```
symbol, instrumentId,
publicState,                 # from R2/A3; never CONFIRMED
attentionPriority,           # read R2
a3Profiles[],                # DISC_EOD_* copy
tags[],                      # PREOPEN_GAP, ON_MOST_ACTIVE, RVOL_EOD, OI_SPURT,
                             # NARROW, RS_LEAD, HAS_OFFICIAL_EVENT, ...
why[], whyUnknown[],
rvolEod|null,
rs1d|null,
completenessContribution,
researchState=WATCH|WAIT,
canUnlockConfirmed=false
```

Batch also: completeness block + `deliveryQueried=false`.

**Frontend (one shell)**

- `#s3WatchQueue` on All Stocks / Live Ops: WATCH chips + why + UNKNOWN.
- Keep `#s2WeatherStrip` as weather; do not merge S3 into S2.
- Adapter GET; 503 → WAIT copy.
- Files: `frontend/s3-cheap-discovery.js`, `index.html`, `selection-live-adapter.js`, `acceptance-check.js`, `styles.css`.
- Do **not** fill entry/T1 as trades.

---

## 7. Forbidden (instant fail)

- Rebuild A3 five profiles or R2 `_priority()`
- Delivery in S3 (query or UI)
- Volume added on top of R2
- `nse_fii_dii` as stock FII buy
- Unnamed deal labelled FII
- RVOL-TOD from EOD bars pretending to be intraday
- PK/workbench scanners as votes
- Nifty S2 % as a discovery point
- `sourceActivationReady=true`, CONFIRMED, qty
- Dual-start collector
- Pasting S4/S5 overlay into `r5_live.py`
- Dropping names that failed one optional layer (tag UNKNOWN instead)

---

## 8. Tests (must pass)

| ID | Assert |
|---|---|
| T1 | Universe size matches R2/A3 eligible; not hard-capped to 40 |
| T2 | Completeness < threshold → `WAIT_PARTIAL_SCAN`; unattempted ≠ excluded |
| T3 | `deliveryQueried is False`; no MTO keys in S3 loader |
| T4 | Most-active join does **not** change R2 `attentionPriority` |
| T5 | Missing pre-open → `UNKNOWN_NO_PREOPEN`, names still listed |
| T6 | Cash-only missing OI spurt not punished |
| T7 | WAIT_CA / REJECT unchanged; cannot enter WATCH queue |
| T8 | PK/native missing → info tag, score +0 |
| T9 | `canUnlockConfirmed=false`; 0 CONFIRMED; R2 `runHash` unchanged |
| T10 | POST 405; lineage mismatch 503 |
| T11 | Existing `test_attention_order.py`, `test_cash_a3_discovery.py` if present, `test_s2_market_weather.py`, `test_r5_live_structure.py` still pass |

```
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s3_cheap_discovery.py tests/test_s2_market_weather.py tests/test_attention_order.py tests/test_r5_live_structure.py tests/test_r6_live.py tests/test_evidence_radar.py -q
cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Scratch → `delete/s3_discovery_wip_<date>/`. No `tmp_*.py` in repo root.

---

## 9. Docs (short)

Patch `fileindex.md`, `docs/BUILD_STATUS.md`, `docs/DECISIONS.md` (**D-046**: S3 cheap discovery joins A3+R2; not a second ranker; delivery excluded; not CONFIRMED), `docs/VALIDATION.md`, remaining_build README.

Do **not** mark S4/R5 structure complete, R8 native scanners done, or File A first CONFIRMED.

---

## 10. Stop

Do not start S4 geometry as trades, R12 options, Kelly, OpenAlgo, or `sourceActivationReady=true`.

**Success observed:**

1. Full eligible universe scanned cheaply; completeness number is real.  
2. WATCH queue shows A3 reason **plus** honest UNKNOWN for pre-open/OI/RS when missing.  
3. R2 order unchanged (volume not added twice).  
4. No delivery anywhere in S3 JSON.  
5. Public state still **0 CONFIRMED**.

That is S3: **find who to look at today, cheaply, without pretending the expensive proof already ran.**
