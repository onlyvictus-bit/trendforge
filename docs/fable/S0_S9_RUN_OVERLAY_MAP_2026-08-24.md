# S0–S9 Run Overlay Map — readability funnel drawn ON File A §9 (crosswalk, not a third S-map)

**Date:** 2026-08-24
**Status:** NAVIGATION AID ONLY. This document annotates the EXISTING File A §9 build stages (`new_merge_PLAN_2026-07-18.md` lines 397–491, `SEL-001..010`) with current build status and research overlays. It renames nothing, reorders nothing, adds no gate, and grants no authority. File A remains supreme.
**Status source:** `docs/BUILD_STATUS.md` 2026-08-23 checkpoint + 2026-08-24 S3 entry (+ fileindex 2026-08-24 entries). Re-verify before use.

---

## The two axes (unchanged)

| Axis | Meaning |
|---|---|
| **S0–S9** | What happens to a stock in ONE scan run (the funnel). Every live scan walks all built stages. |
| **R0–R18** | Build order: which slices of that funnel exist in code today. |

You never pick S or R. R answers "is this stage real yet?"

## Stage-name discipline (binding)

- Build IDs are File A `SEL-00x` only (`§9.3`). FMR-002 story labels differ (**story S4 = shortlist; File A S4 = structure — never swap**).
- This overlay introduces NO new stage numbers. Everything below hangs annotations on S0–S9.

## THE MERGED MAP

Legend: `[R*✓]` implemented (with ceiling) · `[R*⏳]` partial/prompt-only · `⊕` research overlay annotation (not File A law)

**SPINE vs SIDE-SCREENS (read this first):**
The LIVE runtime spine today is `R1 → R2-A → R3(diagnostic) → R4 → R14 → R5 → R6`.
**S2 weather and S3 cheap-discovery are side screens** — real coded rooms that
READ the spine but are not yet read BY anything downstream (see WIRED vs ROOMS).
The ASCII below draws the DESIGNED funnel; arrows marked ✗wire in the gaps
table do not exist at runtime yet.

```text
S0 [R0◐ R1✓] DATA GATE         source role · transport · schema · raw hash ·
 │                             freshness · revision · valid-empty semantics
 │                             R1 = disposition BUNDLE (evidence), not the
 │                             whole gate: R0 contract work stays ◐
 │                             FAIL → named failure ceiling per source;
 │                             ⊕ stop-the-whole-run on corrupt file, never
 │                              per-stock silent drop
S1 [R2✓R4✓R14✓] SAFETY         PIT universe · identity pin · CA join (hash-
 │                             matched into S4) · calendar · circuit ·
 │                             ban/MWPL · CASH side ✓
 │                             MCX local master [R11 ⏳] → MCX names WAIT
 ▼                             exclusions recorded with reasons
S2 [CODED ✓ WAIT-only] WEATHER Nifty/VIX/breadth/sector/commodity CONTEXT TAG
 │                             ceiling WAIT · validator blocks votes/rank
 │                             DESIGNED to veto/downweight at S7 gates,
 │                             NOT WIRED YET: nothing outside this module
 │                             reads it (grep-verified) · Nifty % printed
 │                             20.15 once → freshness suspect path exists
 ▼
S3 [R2-A✓ + projection CODED]   cheap-discovery ADDITIVE over R2 universe:
 │   CHEAP SCAN                 RVOL(EOD)·RS(1d/5d)·preopen·OI spurts·deals
 │   route + watch queue live   GET /…/cheap-discovery{,/watch}
 │                             ceiling LIVE_S3_WATCH_WAIT_ONLY · ≥0.95
 │                             else every WATCH demoted +WAIT_PARTIAL_SCAN
 │                             (0.95 is a partial-scan FLAG — it never proves
 │                              the scan was complete)
 │                             NOT the WATCH owner of record: docstring +
 │                             code — never rebuilds A3 / never re-ranks R2
 │                             native scanners [R8/R13 ⏳]
 ▼
S4 [R5 ✓] STRUCTURE            CLOSED-bar owns DIRECTION OF THE CLAIM;
 │   ★ claim-direction owner   PUBLIC state still owned by S6→S7 only
 │                             breakout/acceptance · NR/compression · trend ·
 │                             optional pattern lane (harmonic/Elliott lab =
 │                             SEPARATE overlay lane, ⊕ chart-NONE → falls
 │                             out of structure claims → WATCH/WAIT side)
 │                             requires hash-matched R14 CA join; zero CONFIRMED
 ▼
S5 [R6 ✓ bounded] ENRICH       WIRED BASE = R2 WATCH top-40 (code literal:
 │                             why=["R2_ATTENTION_BASE"]) — S4-survivor
 │                             gating NOT wired; R5 setups arrive as
 │                             stickers/bonus, not a filter
 │                             delivery · futures OI+BASIS · options
 │                             timeline [R12 ⏳] · deals · pledge · events
 │                             walls/gamma/max-pain today = ⊕ context ROOMS
 │                             (one family when they become claims)
 │                             ⊕ illiquid options → NA · budget-capped
 ▼
S6 [R3 ✓ thin] FAMILY RESOLVE  FUS-009 engine real: correlation groups · twins
 │                             merged · authority + contradiction +
 │                             independence rules; live claim feed ≈ single
 │                             FTR-040 cash participation claim → all rows
 │                             WAIT (that is WHY, not a bug)
 ├─⊕ M-FACTOR VIEW             rebuilds R5 claims in its own BFF — view,
 ▼                             must never sit on the spine as resolver #2
S7 [R2-B ⏳ CODED ✓] STATE GATES  LIVE profile = PRF-003-SWING-EOD
 │                             (STRUCTURE required; PARTICIPATION / EVENT /
 │                              RS-companion alternative; weather + blackout
 │                              fail-closed flags). Other horizons return
 │                              empty boards + WAIT_HORIZON_*.
 │                             PRF-001/002/004–007 remain plan IDs for now.
 │      ┌──────────┬──────────┬──────────┬─────────┐
 ▼      ▼CONFIRMED ▼WATCH     ▼WAIT      ▼REJECT    activation=false ⇒
        unreachable recheck    show why    show why  CONFIRMED unreachable
        (draft only, next bar  (conflict /
         not executed)          partial scan)
 │
 ├──▶ IDEA CARD [R15 ◐ shell]  geometry entry/stop/targets mostly NULL on
 │                             live M-Factor rows · qty=0 ·
 │                             ⊕ zone grade A/B/C overlay (Hybrid V3,
 │                               RESEARCH_PROXY_NOT_CALIBRATED) — not S7 output
 ▼
S8 [✓ CODED 08-25] SAVE      ONE reconstructable blob: lineage S2–S7 pins,
 │                           completeness tuple, STO-008 state events vs prior
 ▼                           run, what-changed kinds · immutable store
S9 [R16 ⏳ NOT_CODED] PIT     homework prompt exists; labels only after S8 runs
                            exist across sessions · NO AUTO-TRADE ever
```

## Overlay register (where each readability-funnel idea lives)

| Funnel idea (earlier draft) | Official home | Label |
|---|---|---|
| Stop entire run on bad data file | S0 failure-specific ceilings | consistent with ceiling law; whole-run-stop semantics = overlay proposal (⊕) until mapped to a named ceiling code |
| Market-weather TAG vetoing at gates | S2 context → S7 profile gates | already File A law (`SEL-003` never confirms alone) |
| CHART VOTE block | S4 closed-bar pack (pattern lane optional) | harmonic/Elliott lab stays separate overlay lane |
| EXPENSIVE JURY (M-Factor/OI/deals) | S5 shortlist enrichment + S6 resolution display | M-Factor = view only |
| FAMILY CAP SCOREBOARD | S6 FUS-009 correlation groups | binding law, not overlay |
| HYBRID V3 TRIANGULATE zone grade A/B/C | IDEA CARD geometry (S7 output) | RESEARCH_PROXY_NOT_CALIBRATED |
| Illiquid options → NA | S5 enrichment quality rule | consistent with fail-closed law |
| OI quadrant FACT codes | S5 claim vocabulary | replaces buildup folklore |
| Weekly diary/PIT review cadence | S9 practice | would require R16 scoping; not currently planned |

## Current build truth (one line each, verified 2026-08-24)

`R0 partial(A closed/B provenCount=0/C quarantined)` · `R1 ✓` · `R2 ✓(attention order, no CONFIRMED)` · `R3 ✓ WAIT-only` · `R4 ✓ identity-pin only (no vote)` · `R5 ✓ zero CONFIRMED` · `R6 ✓ Top-40 stickers` · `R7 offline only` · `R8/R9 ⏳` · `R10 ✗` · `R11 ⏳` · `R12 ⏳ (OI rooms ≠ this)` · `R13 ✗` · `R14 ✓ WAIT-only` · `R15 ◐ shell` · `R16 ⏳ fixtures` · `R17 boundary-only, capability ABSENT` · `R18 ⏳ contracts`
Live run 2026-08-24 evening: backend 1,123 passed / 6 failed (same six as 08-23 checkpoint) · frontend 185/185 · `sourceActivationReady=false`.

## VERIFIED SAFE — what is NOT broken (keep visible)

| Safety fact | Where enforced |
|---|---|
| No CONFIRMED leak anywhere (activation=false) | S7 ceiling + every stage validator |
| S2 never votes a stock | `RESEARCH_CONTEXT_NOT_CONFIRMED` validator blocks rank/unlock |
| S3 cannot emit or unlock CONFIRMED | row + batch validators reject at load |
| qty = 0 on ordinary rows | IDEA CARD contract |
| R14 CA join before R5 structure | hash-match gate, 503 if mismatch |
| M-Factor stays a VIEW; cannot write state | separate BFF, no resolver seat |

## WIRED vs ROOMS — the pipe gaps (the map's action list)

Stages exist as rooms; these arrows are documentation, not runtime yet.
✓c = verified in code by this map's audit greps.

| # | Gap | Evidence |
|---|-----|----------|
| 1 | ~~S2 tag does NOT reach S6/S7 gates~~ **SOLVED 08-24 late (display layer)**: `s6_family_resolution.py` attaches weather as context block, `canSupportConfirmed=false`, never satisfies required families. Gate-MATH inside PRF profiles still deferred to R2-B | ✓c: s6_family_resolution.py:16-17,102,148-156 |
| 2 | S3 is additive projection, NOT the WATCH owner of record — never re-ranks R2, completeness flags its own DTO only | module docstring + validators |
| 3 | ~~S4 does not consume S3 queue~~ **BY DESIGN (closed 08-24)**: S4 pack is a pure projection of persisted R5, which already processes the FULL eligible universe — wiring S4→S3 would *shrink* structure coverage to ~40 names and couple safety-critical claims to an attention heuristic. Attention correctly rations only the EXPENSIVE stage (S5 gate, shipped same day). Hub-and-spoke, not a linear pipe, at this joint | ✓c: s4_structure_pack.py docstring "never re-scans bars… extends persisted R5"; r5_live processes all attention rows |
| 4 | ~~S5 shortlist = R2 WATCH top-40~~ **SOLVED 08-24 late**: `s5_shortlist_enrichment.py` requires ≥1 CG_PRICE_STRUCTURE/CG_COMPRESSION rep; fallback = R2 WATCH ∩ latest R5 detected_setups, never bare WATCH-40 | ✓c: s5_shortlist_enrichment.py:5-6,329-341 |
| 5 | ~~S6 feed = one cash claim~~ **SOLVED 08-24 late ×2**: r5 rows publish claims+facts (`s6_claim_feed.merged_feed`) AND builder's `s6_family_resolution.py` ingests S5 OPTIONS_PACKAGE + uses `structure_claims_from_r5` on batch5 | ✓c: s6_family_resolution.py:51,201,247 |
| 5b | S2 display-half solved at both layers: `R3ResolutionV1.market_context` + S6 block; GATE-MATH still deferred to profiles/R2-B | same sources |
| 6 | ~~S7 profiles are plan IDs~~ **PRF-003 NOW WIRED (08-24 late)**: `s7_state_gates.py` runs PRF-003-SWING-EOD live (STRUCTURE required + PARTICIPATION/EVENT/RS-companion alternative + weather/blackout fail-closed flags); PRF-001/002/004–007 return empty boards + `WAIT_HORIZON_*`/`WAIT_MCX_MASTER`; legacy `PRF-R3-LIVE-DIAGNOSTIC` retained inside M-Factor BFF | ✓c: s7_state_gates.py + BUILD_STATUS 08-24 late |
| 7 | S1 MCX master [R11 ⏳] → MCX names must WAIT | File A §9 SEL-002 |
| 8 | Options timeline/walls as CLAIMS into S6 = [R12 ⏳]; today they are ⊕ rooms | OI-rooms prompt status |
| 9 | Weather freshness: Nifty % printed 20.15 once → suspect-path exists, treat tag as unproven | parser fix note |
| 10 | ~~S8 one-blob reconstruction missing~~ **SOLVED 08-25**: `/scans/latest` builds+pins lineage S2–S7 (S2 via derived id; S3 completeness tuple) into one immutable blob; Hybrid stays hash-pinned non-voting overlay | ✓c: `selection/s8_persist_run.py` + BUILD_STATUS 08-25 |
| 11 | Idea-card geometry mostly null on live rows; zone grade = overlay only | M-Factor BFF DTO |
| 12 | 6 pre-existing backend test failures still block "working" claim | full-suite runs |

Closing #1/#4/#5 (make S2 a readable gate flag, gate S5 on S4 survivors, widen
S6 claim feeds) plus R10's pipe DSL is what turns rooms into ONE pipe.

### Builder handoff — S4/S5/S6 module review 2026-08-24 (13 findings, 0 P1)

Top fixes owed to the parallel builder (full list in session log):
1. P2 s5:340-343 fallback labels every survivor `CG_PRICE_STRUCTURE` even when setup is RVOL/NR-only — derive group from setup prefix.
2. P2 s5:313-320 gate tests `correlation_group` presence, not `claim_id is not None` → claimless rows slip in; two different shortlists exist for one pack (s4:412-420 is claim-based).
3. P2 all six models: `acceptance_ceiling`/`state_ceiling` are defaults, not pinned invariants — tampered stored payloads load happily. Copy r5_live's load-time validator pattern.
4. P2 zero tamper-roundtrip tests in the three new test files (researchState:"CONFIRMED", canUnlockConfirmed:true, etc. must raise at model_validate).
5. P3 s6:340 pins completeness=1.0, disabling WAIT_PARTIAL_SCAN diagnostics — pass R5/R2 completeness through.
6. P3 s5:259 leaks banned positioning vocabulary (`LONG_BUILDUP`…) via raw quadrant strings — map to neutral OI↑price↑ codes.
Plus 7 more P3s (model_copy validator bypass, duplicate-extra crash, trigger price precision, S5 lineage trust, dead guard, None→0.0 coercion).

## Rules this map obeys

1. No third S-map: numbers/names are File A §9 verbatim (`§9.3`).
2. Story-vs-build trap respected: this map never says "S4 shortlist".
3. Overlays are labelled ⊕ and grant no gate, state, or authority.
4. One public-state owner: S6→S7 resolver + profiles (`§9.4`); views/cards project, never re-score.
