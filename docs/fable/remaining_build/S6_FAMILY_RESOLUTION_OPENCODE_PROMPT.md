# OPENCODE BUILD PROMPT — File A S6 family resolution
## FUS-009 on S4+S5 claims — research strength, not CONFIRMED, not Combined_Score

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. Shell: PowerShell. Chain with `;` not `&&`.

Copy this **entire file**. Think first.

**S4 structure and S5 enrichment are upstream.** This ticket is **S6 only** = File A `SEL-007`.

Do **not** rebuild S1–S5, R1–R5, R14, or S2.  
Do **not** set `sourceActivationReady=true`. Do **not** emit CONFIRMED. **CONFIRMED is S7** (profile gates) after R2-B unlock — out of scope.  
Do **not** paste Hybrid `p̂`/Kelly. Do **not** dual-start the collector.

Options: S6 **fuses** an S5 `OPTIONS_PACKAGE` if present. Do **not** re-implement `OPTIONS_INTELLIGENCE_PLAN.md` here. Open it only to respect: one options family, GEX not dealer, missing chain = UNKNOWN not a vote.

---

## 0. Outcome (done means this was **observed**)

1. One GET returns, per shortlist name: **family map** (support / oppose / missing / conflict / context-only), **one representative per correlation group**, `evidenceStrength` labelled **“not win probability”**, `conflict` flag, `why[]` / `whyUnknown[]`.
2. Public `resolutionState` is WATCH or WAIT (or REJECT if S1 already rejected). **0 CONFIRMED.**
3. Volume/gainer/RVOL/R2 cash = **one** `CG_ACTIVITY_SESSION`. NSE+BSE same deal = **one** `CG_EVENT_ROOT`. PCR+walls = **one** `CG_OPTION_CHAIN`. Breakout+new high = **one** `CG_PRICE_STRUCTURE`.
4. S2 Nifty % / VIX = `MARKET_AND_SECTOR_CONTEXT` **context-only** (weight may be 0 for confirmation; must not create a stock BUY).
5. Existing `test_r3` family tests / `test_evidence_radar` fusion caps / R5 still pass. R2 `runHash` unchanged.

---

## 1. What S6 is (File A §9 wins)

| Stage | ID | Work | Ceiling |
|---|---|---|---|
| **S6** | `SEL-007` | Resolve claims by family and correlation group; authority, contradiction, independence | Family resolution + evidence strength |
| **S7** | `SEL-008` | Profile gates → four-state | **Not this ticket** |

| This ticket IS | This ticket is NOT |
|---|---|
| FUS-009 over **S4+S5 claims** | R3-only FTR-040 diagnostic as the whole fuse |
| Research `evidence_strength` | Win rate / p̂ / Combined_Score owning state |
| CONFLICT → neither BUY/SELL seat | Silent max of two opposite events |
| WAIT ceiling | File A first CONFIRMED |

**Already live:**

- `selection/r3_live.py` — WAIT diagnostic, **one** FTR-040 NSE EOD PARTICIPATION claim, `corroboration_epsilon=0`, `confirmed` forbidden. Intraday/MCX/options/events **non-directional until contracted**.
- `selection/evidence_radar/fuse.py` — horizon fuse, context families weight 0.
- `selection/resolver.py` — canonical resolver.

S6 **must ingest S4 structure claims + S5 enrichment claims**, not only the cash FTR-040 adapter. Do not delete R3. Extend adapter or add `s6_resolve.py` that **calls** `resolve_evidence`.

---

## 2. Authority

| Rank | File | Use |
|---|---|---|
| 1 | `docs/fable/new_merge_PLAN_2026-07-18.md` | §11.1–11.3 families + groups + formula; §10.4 CONFIRMED prerequisites (do **not** satisfy them here) |
| 2 | Locked R0/R1/R2 plan | R3 WAIT; FUS-009 live diagnostic |
| 3 | `docs/OPTIONS_INTELLIGENCE_PLAN.md` | One OPTIONS_PACKAGE; no dealer GEX |
| 4 | Hybrid File B | Fusion detail if File A points; no qty |

---

## 3. Resolver contract (copy, do not invent Combined_Score)

Families:  
`TRADABILITY_AND_SAFETY`, `MARKET_AND_SECTOR_CONTEXT`, `STRUCTURE`, `PARTICIPATION`, `DERIVATIVES_OI`, `OPTIONS_CONTEXT`, `EVENT_AND_SPONSOR`, `MACRO_AND_COMMODITY_CONTEXT`, `SPONSOR_DELAYED_CONTEXT`, `EXPERIMENTAL`.

```text
eligible_claims = fresh, authority-allowed, profile-valid claims in family f
representative = highest quality-adjusted claim per correlation group
family_base = max(representative strengths)
corroboration = epsilon * bounded extra independent groups
family_score = cap_f(family_base + corroboration) * contradiction_penalty_f
```

Live R3 uses **`epsilon=0`**. Keep epsilon 0 unless a File A versioned profile says otherwise. Do not sneak corroboration bonuses.

`evidence_strength` = versioned weighted aggregate **after** required-family zeros and WAIT ceiling.  
Label exactly: `Evidence strength - not win probability`.

Required families come from the **ACTIVE VERSIONED PROFILE** (File A §9.2) — read them, never hardcode. Today's wired default = live diagnostic profile (**STRUCTURE + PARTICIPATION** missing → strength 0 / WAIT). When PRF-001..007 wire, their own required sets apply (e.g., PRF-003 swing substitutes RS/EVENT for PARTICIPATION).

Context families (S2 weather): **rank weight may be >0** (live resolver = 0.15 — rank is not confirmation), but `can_support_confirmed` stays **false** and a context claim can never SATISFY a required confirmation family.

PK shadow: `CG_PK_SHADOW_NATIVE` — shadow never adds a vote.

---

## 4. Claim inputs (read, don’t recompute)

| Source | Claims to ingest |
|---|---|
| S1 / R2 | REJECT/WAIT_CA/ban veto; R2 `evidence_direction` as cash participation read |
| S2 | Market weather as **context** claims, `can_support_confirmed=false` |
| S4 / R5 | Structure tags, NR, nextTrigger — `CG_PRICE_STRUCTURE` / `CG_COMPRESSION` |
| S5 / R6 | Delivery, FO package, OPTIONS_PACKAGE, named deal, delayed MF, SHP context |
| R3 adapter | Keep FTR-040; **do not emit a second** same-root participation claim |

If S5 GET missing, ingest R6 + radar facts. If S4 missing, ingest R5 `detected_setups`. Fail 503 on lineage mismatch, not on optional empty options.

---

## 5. What to build (paths — reuse the designed shell)

Call existing `resolver.resolve_evidence`. Do not fork a third fuse that disagrees with R3 + radar caps.

**Create / touch**

| Role | Path |
|---|---|
| New | `D:\TrendForge\backend\trendforge_api\selection\s6_family_resolution.py` (or extend `r3_live.py` **without** deleting FTR-040) |
| Tests | `D:\TrendForge\backend\tests\test_s6_family_resolution.py` |
| Route | `D:\TrendForge\backend\trendforge_api\main.py` — **extend** `GET /api/v1/selection/resolution` **or** sibling `GET /api/v1/selection/s6-resolution`; POST 405 |
| Frontend | `D:\TrendForge\frontend\s6-resolution.js` |
| Inspector | `D:\TrendForge\frontend\index.html` `#q5Inspector` `#q5InspectorTabs` `#q5InspectorPanel` — **Decision** tab: support / oppose / missing |
| Live Ops | `#liveDecisionPanel` `#liveDecisionList` — research records only |
| Radar boards | `frontend/evidence-radar.js` `#evidenceRadarPanel` may **read** fused direction for display; do not rewrite R2 `publicState` |
| Adapter | `frontend/selection-live-adapter.js` — bind the extra GET; keep name count = fetch count |
| Q5 contract | `frontend/q5-contract.js` — public states unchanged; no CONFIRMED from S6 |
| Styles + accept | `frontend/styles.css`, `frontend/tests/acceptance-check.js` |

DTO row: families{}, conflict, evidenceStrength, evidenceStrengthLabel, missingFamilies[], researchState=WAIT, canUnlockConfirmed=false.

**Do not** create a second inspector. **Do not** overwrite `#flow` (File A S6 there is PK/resolution story — keep labels). **Do not** use `#s4s5ComparePanel` as File A S6.

Ceiling: `LIVE_S6_RESOLVE_WAIT_ONLY`.

**Scratch / delete**

- Scratch → `D:\TrendForge\delete\s6_resolve_wip_<YYYY-MM-DD>\`
- No `tmp_*.py` in repo root
- Do not dual-start the collector

---

## 6. Forbidden

- CONFIRMED (that is S7 + R2-B amendment)  
- Combined_Score / tutorial additive points  
- Second volume vote  
- S2 Nifty up → stock BUY  
- Options metrics as 5 votes  
- `epsilon` bonus without a versioned profile  
- Rewriting R2 attention  
- qty / Kelly as strength  
- Dual-start collector  

---

## 7. Tests

| ID | Assert |
|---|---|
| T1 | Two CG_ACTIVITY_SESSION claims → one participation representative |
| T2 | NSE deal + BSE mirror → one EVENT family |
| T3 | OPTIONS PCR+wall → one OPTIONS_CONTEXT |
| T4 | Opposite independent EVENT groups → conflict=true; researchState not CONFIRMED |
| T5 | Missing STRUCTURE required family → strength 0 / WAIT |
| T6 | evidenceStrengthLabel contains “not win probability” |
| T7 | S2 index claim cannot set BUY alone |
| T8 | `canUnlockConfirmed=false`; 0 CONFIRMED; R2 hash unchanged |
| T9 | POST 405; lineage mismatch 503 |
| T10 | Existing R3/radar fusion tests still pass |
| T11 | Required-family set is read from the active profile object (swapping the versioned profile swaps requirements — no hardcoded STRUCTURE+PARTICIPATION constant) |

```
cd D:\TrendForge\backend
D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_s6_family_resolution.py tests/test_q5_family_resolver.py tests/test_evidence_radar.py tests/test_r5_live_structure.py tests/test_r6_live.py -q
cd D:\TrendForge\frontend
node tests/acceptance-check.js
```

Scratch → `delete/s6_resolve_wip_<date>/`.

---

## 8. Docs (after observed tests — short patches)

| File | Patch |
|---|---|
| `D:\TrendForge\fileindex.md` | S6 files + resolution route |
| `D:\TrendForge\docs\BUILD_STATUS.md` | S6 WAIT fuse over S4+S5; not S7 |
| `D:\TrendForge\docs\DECISIONS.md` | **D-049**: S6 = SEL-007 FUS-009; R3 stays diagnostic; not Combined_Score; not CONFIRMED |
| `D:\TrendForge\docs\VALIDATION.md` | family-cap tests + acceptance |
| `D:\TrendForge\docs\fable\remaining_build\README.md` | Status row |
| `D:\TrendForge\docs\ARCHITECTURE.md` | S6 consumes R3 resolver; does not own public_state |

Do **not** mark S7, R2-B unlock, or File A first CONFIRMED done.  

---

## 9. Stop

Success: inspector shows **which families agree, which conflict, what is missing** — still **WAIT**, still **not a buy stamp**.
