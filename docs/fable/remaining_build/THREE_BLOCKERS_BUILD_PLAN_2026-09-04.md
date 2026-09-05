# Build Plan — Three Blocked Parts (Price-Band Boundary, R5 Structure, Activation)
**Date:** 2026-09-04 · **Status:** PLAN (not executed)
**Companion detail file:** `PRICE_BAND_TECHNICAL_ZONES_BUILD_PLAN_2026-09-04.md`
(same folder — owns all of Part 1's rule matrix, contracts, formulas, and the
50 adversarial tests; this file owns sequencing, ownership, and gates).
**Authority order:** user instruction > File A > AGENTS.md > DECISIONS.md
(D-066/D-067) > tests > current code. Read-only v1: **no broker execution.**

## 0. What is blocked and why (verified 2026-09-04)
- **Part 1 — price-band boundary:** parser keeps `bandPercent`/`hasPriceBand`
  only (`parsers/tradability_source_parser.py:87-96`); gate refuses guessed
  geometry (`selection/tradability.py:304-313` → `WAIT_PRICE_BAND_VALUES_MISSING`).
  Checkpoint confirmed in the normalized store (3,517 band rows @2026-09-02,
  290 ESM rows @2026-09-03, auction NIL valid-empty @2026-07-09); SQLite parse
  tables are archive-only for these keys.
- **Part 2 — R5 structure:** `build_r5_structure_batch` (`selection/r5_live.py:302`)
  is built; readers go through `_hash_matched_r5_or_503` (`main.py:1630`);
  persistence exists (`persist_r5_structure_batch`, scheduler
  `market_data_scheduler.py:544`). No current hash-matched batch exists because
  input lineage is stale (bhavcopy 2026-08-03, filings 2026-07-30).
- **Part 3 — activation:** checker built (`selection/r2b_live.py`: five named
  confirm-path sources — `nse_bhavcopy_eod`, `nse_fno_ban`, `nse_fo_bhavcopy`,
  `nse_index_close_eod`, `nse_corporate_filings_actions` —
  `authorizedCount` match, all-five rule at `:136`,
  `amendment_flip` at `:314`). Currently locked: four stale sources, MWPL
  unproven (`MWPL_MISSING` in `mwpl_b.py`, `cash_a2_identity.py`, options
  `mwpl_gate.py`), compiler `gate_permission=false` everywhere
  (`source_inventory_compiler.py:341,505,1772`), `canVote=false` (R0-B/R0-C).

## 1. Deep-plan verdict — the boundary-source decision (the only hard choice)
Aspects swept: goal (hard limits without guessing), data (band% exists,
rupee limits don't), mechanism (calculate vs download), cost (tick-master +
base loader + ~20 geometry tests), risk (wrong limits worse than WAIT).

- **Scientist:** exact rupee limits are not downloadable on the free lane
  (member-only EOD DB files); only prev-close × band% × tick-grid is provable.
- **Engineer:** calculation is ~2 small modules reusing R14 + scheduler tables;
  blast radius confined to `_price_band_component`.
- **Economist:** cost of a wrong limit (false REJECT/PASS) exceeds cost of
  WAIT; every WAIT carries its blocker code so the UI stays informative.
- **Superforecaster:** reference class = prior TrendForge parser/gate tickets;
  base rate of first-pass green ~70%; 80% CI for Parts 1+2 code work: 3–6
  sessions; data-dependent steps are calendar-bound, not effort-bound.
- **Red team:** likeliest killer is building geometry on the phantom
  3,517-row checkpoint (unpersisted evidence) — killed by Sequence step 1's
  STOP gate. Second killer: silent tick-grid drift — killed by monthly-master
  freshness window + hash stamping.
- **Domain advocate:** matches standing law — fixtures never become production
  evidence (AGENTS.md), R9-skipped intraday stays out, no second pipelines.
- Independence: scientist+engineer share the codebase (one family);
  forecaster base rate and red-team failure evidence are independent.

```
CANDIDATES:
| # | Approach | Mechanism | Score (fit/comply/base/falsify/reverse) | Kill risk | P(success) |
| 1 | Calculated geometry, proven inputs | base=R14-adjusted prev close × band% → tick-grid align, stamp or WAIT | 5/5/4/5/5 | phantom-checkpoint reuse | 78% (75–82%) |
| 2 | Member EOD DB files | licensed feed download | 2/5/1/5/5 | feed doesn't exist here | 15% |
| 3 | WAIT indefinitely | status quo | 3/5/5/5/5 | permanent dead feature | n/a (safe, zero value) |
RECOMMENDATION: Candidate 1 — calculated geometry with per-row evidence stamps.
CONFIDENCE: 78% (75–82%) from 3 independent families: forecaster-base-rate, red-team-failure-evidence, scientist-constraint.
WEAK LINK: tick-master source availability (if no monthly master is obtainable, geometry stays WAIT by design).
CHEAPEST TEST: Sequence step 1 rerun — if band rows land in the canonical DB with hashes, P rises to ~85%.
```

Triangulate grade on the whole three-part plan: families = code-evidence
(verified modules), official-docs (NSE/SEBI citations in companion file),
DB-observation (live counts) → **TIGHT overlap → grade A**. Proceed.

## 2. Part 1 — price-band boundary (detail: companion file sections 2–5, 8, 11–13)
Work items: (a) checkpoint re-verification rerun into canonical DB, STOP gate;
(b) monthly tick-master parser (`parsers/`); (c) R14-aware base-price loader;
(d) `EXCHANGE_LIMIT` geometry inside `_price_band_component` keeping every
existing code (add flex-unknown, MW-halt, PPCA-band paths only);
(e) per-symbol `geometry{lo,hi,base,rule,tickGrid,hash}` evidence.
Out: honest `WAIT_*` rows, never invented limits. All 16 companion sections
apply; especially coding style (§11), 50 tests (§12), KEEP/REJECT table (§15).

## 3. Part 2 — R5 structure rebuild (no R5 code change)
Work items: (a) refresh the input lineages via the normal scheduler path
(the SEVEN fields `_hash_matched_r5_or_503` compares — R1 bundle id+hash, R2
run id+hash, `collector_run_id`, `cash_pipeline_fingerprint`,
`permission_fingerprint`, R14 run id+hash; a mismatch on ANY one keeps
`R5_STRUCTURE_NOT_READY`); (b) one successful scheduler run through
`persist_r5_structure_batch`; (c) confirm `_hash_matched_r5_or_503` serves a
current batch; (d) add gate-hash citation into R5 `why_wait` for band-WAIT
rows (S8 already stores the gate hash per D-066).
Out: `R5_STRUCTURE_NOT_READY` clears only on fresh hash-matched lineage.

## 4. Part 3 — sourceActivationReady unlock (governance + data, in order)
Work items: (a) refresh the four stale sources (cash bhavcopy, corporate
actions, F&O ban, F&O bhavcopy) to current last-goods — re-check each against
its `source_freshness` window at execution time, since staleness is dated;
(b) MWPL stays `MWPL_MISSING` until a proven official percentage artifact
exists for source key `nse_mwpl_percentages` — no percentage gate is invented,
ever; (c) DESIGN FIRST: no code path anywhere grants `gate_permission=True`
today, and the compiler requires ALL contracts permitted
(`source_inventory_compiler.py:1772`), so activation is unachievable even with
fresh data until a human-review grant record/contract exists — specify its
fields, approver, and audit trail before any flip is attempted; (d) explicit
operator activation approval recorded in DECISIONS.md; (e) `amendment_flip`
then flips from observed evidence alone.
Out: activation remains a safety state until every precondition is observed.

## 5. Sequencing (dependencies, not preferences)
1. Part 1(a) checkpoint rerun → STOP if evidence absent.
2. Parts 1(b–e) geometry (needs 1 + R14 + tick-master).
3. Part 2 lineage refresh + scheduler run (needs fresh inputs incl. Part 1 rows).
4. Part 3(a–c) data + permission refresh (needs 1–3 green).
5. Part 3(d–e) approval + observed flip.
6. Full suite + live battery + docs + registry/CSV evidence update.

## 6. Gates (each is STOP-on-fail)
- G0 evidence: band/ESM/auction rows + hashes in the normalized store.
- G1 geometry: tests §12.1–20 green; S7 suite green; live 200 honest.
- G2 R5: current hash-matched batch served; replay identity incl. gate hash.
- G3 activation: all-five observed current; MWPL still missing-by-design;
  approval recorded; flip observed, never forced.
- G4 system: full backend suite + frontend acceptance + battery + docs.

## 7. Fixture-vs-live boundary (tester rule — violate this and the gates lie)
- Unit tests MAY use fixtures (`hybrid_v2/tests_support`, monkeypatched
  `storage.DB_PATH`): geometry math, gate logic, hash-match logic.
- Prod paths MUST use observed evidence only: band geometry reads the
  normalized store, R5 persists from scheduler lineage, the activation flip
  reads live last-goods. No fixture object may cross into these paths.
- S8 replay must cite the gate hash; a replay that cannot reproduce the exact
  WAIT/REJECT row is a failure, not a pass.

## 8. Approvals required (operator, before proceeding past each)
| Step | Approver | Form |
|---|---|---|
| Tick-master source acceptance | operator | DECISIONS.md entry naming the file + cadence |
| Collector rerun (bands/ESM/auction, five R5 inputs, four activation inputs) | operator | go-ahead; results recorded with hashes |
| Grant-record design | operator | fields + approver + audit trail specified |
| Activation approval | operator | DECISIONS.md entry; flip observed afterwards |

## 9. Effort and rollback
- Part 1 code (tick parser, base loader, geometry): 80% CI 3–6 sessions
  (reference class: prior parser/gate tickets); data steps are calendar-bound.
- Part 2: one scheduler run + verification; effort trivial, calendar-bound.
- Part 3: grant design 1–2 sessions; flip itself is automatic once observed.
- Rollback per part is the fail-closed default: geometry stays WAIT, R5 stays
  NOT_READY, activation stays false. No rollback procedure beyond "do not
  force"; any forced flip is a defect, not a recovery.

## 10. Unresolved (do not build on assumptions)
Q1 checkpoint-vs-DB mismatch. Q2 upper-slab tick table NSE-primary. Q3 SME
fixed % NSE-primary. Q4 40% mechanics NSE-primary. Q5 lint owner/route rule.
Q6 MWPL standing. Q7 activation approval standing. See companion §16.

