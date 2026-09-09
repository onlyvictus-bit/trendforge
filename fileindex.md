<!-- CURRENT_STATE_HISTORY_BOUNDARY: system-brain-navigation -->
> **Current code/readiness summary:** [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md). Historical material is preserved separately and must not override current runtime evidence.

# TrendForge Document Index

> **Current navigation layer.** Use this file to locate the present architecture, readiness, implementation-flow and historical references. Runtime behavior always wins over documentation.

## 1. Start here for future development

### System brain, architecture skeleton and implementation roadmap

**File:** [`docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md`](docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md)

**Purpose:** permanent reference for understanding how TrendForge is built and how it should evolve safely.

Use it to understand:

- end-to-end ingestion -> normalization -> discovery -> strategy -> gates -> publication -> validation flow,
- the distinction between instrument, opportunity and decision version,
- discovery versus strategy direction,
- equity intraday, equity swing, event/ownership and commodity strategy boundaries,
- source timing, availability, revisions, identity, corporate actions and contract rollover,
- feature reuse, cache keys, dependency-driven recalculation and invalidation,
- safety/event/tradability boundaries,
- immutable publication and UI freshness/history behavior,
- outcome tracking and point-in-time research validity,
- verified findings **A01-A44**,
- ordered implementation roadmap **TF-00 through TF-25**,
- acceptance invariants that future patches must preserve.

**Why it was created:** the project contains many sources, registries, stages, UI panels, historical plans and partially connected strategy components. This reference prevents future upgrades from reading one function or one historical document in isolation and accidentally breaking the wider decision chain.

**Important:** declarations, registry entries and UI labels are not proof of runtime activation. The system-brain document uses `VERIFIED RUNTIME-CONNECTED`, `DECLARED BUT NOT PROVEN ACTIVE`, `FIXTURE/TEST ONLY` and `NOT VERIFIED` to preserve that distinction.

### Engineering audit crosswalk and preserved requirements

**File:** [`docs/TRENDFORGE_ENGINEERING_AUDIT_CROSSWALK_AND_PRESERVED_REQUIREMENTS.md`](docs/TRENDFORGE_ENGINEERING_AUDIT_CROSSWALK_AND_PRESERVED_REQUIREMENTS.md)

**Purpose:** verified crosswalk between the detailed 44-finding/26-ticket engineering audit and the current System Brain/trading-brain references.

Use it to understand:

- which detailed audit requirements are already preserved in Git,
- the stage **0 -> 14** audit crosswalk from collection through research validity,
- the exact collector/persistence versus screen event-input discrepancy,
- the R16 proxy-plan / missing-S8-geometry limitation,
- the same-day decision-version and availability-time requirements,
- why attention priority must not become evidence strength,
- why snapshot consistency is not the same as freshness/precomputation,
- the historical source/test inventory boundary from the original audit,
- which original generated audit artifacts are **not proven present in the repository**.

**Important:** historical audit test counts and source inventories are preserved as audit evidence only. They must not replace newer branch-specific CI/runtime evidence.

### Trading brain / stock-picking strategy-engine reference

**File:** [`docs/TRENDFORGE_TRADING_BRAIN_STRATEGY_ENGINE_REFERENCE.md`](docs/TRENDFORGE_TRADING_BRAIN_STRATEGY_ENGINE_REFERENCE.md)

**Purpose:** plain-English future-build reference for the actual TrendForge opportunity-thinking engine across equity intraday, equity swing, reversal, event/ownership and commodities.

Use it to understand:

- why `INSTRUMENT != OPPORTUNITY != DECISION VERSION`,
- why TrendForge must not become one universal bullish stock score,
- the discovery-brain -> strategy-router -> strategy-specific-opportunity flow,
- how one instrument can simultaneously carry continuation, reversal, swing and event opportunities,
- the intended independent equity swing, equity intraday continuation, reversal, event/ownership and commodity brains,
- commodity contract identity, expiry/roll/tender/OI/liquidity requirements,
- why ranking occurs only inside comparable groups,
- how safety, tradability, liquidity, events and cost remain separate from direction,
- how R-HIST acts as the point-in-time notebook for the trading brain,
- how outcomes, frozen ML datasets and model versions must retain exact historical evidence,
- the TF-10 through TF-25 future build relationship for the trading brain.

**Important:** this document describes intended architecture and future build boundaries. It does not claim that intraday or commodity strategies are already end-to-end complete or that trading/model/execution is authorized. Current runtime evidence and `docs/CURRENT_STATE.md` remain authoritative.

---

## 2. Current code/readiness summary

**File:** [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md)

**Purpose:** concise current implementation/readiness summary. Use this before treating any older statement such as "current", "implemented", "next" or "passed" as still true.

Current capability/readiness concepts must remain separate:

- code implemented,
- tests passed,
- real data observed,
- data currently fresh,
- strategy/source activation approved,
- PIT approved,
- model approved,
- execution authorized.

---

## 3. Atomic research snapshot contract

### Contract

**File:** [`docs/ATOMIC_RESEARCH_SNAPSHOT.md`](docs/ATOMIC_RESEARCH_SNAPSHOT.md)

**Purpose:** explains the one-request/read-snapshot consistency architecture used by the research UI.

Key owners on the reviewed branch stack:

- `backend/trendforge_api/read_snapshot.py` — request-scoped read transaction,
- `backend/trendforge_api/selection/snapshot_service.py` — read-only response envelope,
- `backend/trendforge_api/selection/s8_service.py` — shared stage assembly,
- `frontend/research-snapshot.js` — frontend snapshot contract validation.

This solves **consistency**, not automatically **freshness**, **precomputation**, **publication completeness** or **low request cost**.

### Verification

**File:** [`docs/ATOMIC_SNAPSHOT_VERIFICATION.md`](docs/ATOMIC_SNAPSHOT_VERIFICATION.md)

**Purpose:** records observed tests and the remaining verification/type-check boundary for the atomic-snapshot work.

---

## 4. Historical project index preserved unchanged

**File:** [`docs/archive/fileindex_before_system_brain_2026-09-08.md`](docs/archive/fileindex_before_system_brain_2026-09-08.md)

**Purpose:** exact preserved pre-system-brain `fileindex.md` blob containing the older dated project notes, feature/stage summaries, build checkpoints and navigation history.

Use it for historical investigation only. Older statements describe their recorded checkpoint and must not override the current code/readiness summary or the current system-brain audit.

It was preserved rather than deleted so future debugging can trace how architecture and implementation claims evolved over time.

---

## 5. Major workflow/navigation reference already in the repository

**File:** [`docs/fable/S0_S9_RUN_OVERLAY_MAP_2026-08-24.md`](docs/fable/S0_S9_RUN_OVERLAY_MAP_2026-08-24.md)

**Purpose:** S0-S9 workflow crosswalk over the project roadmap. Treat it as a navigation/reference map, not proof that every declared stage/profile is currently runtime-connected.

---

## 6. How to use these files before a patch

For any important change:

1. Read `docs/CURRENT_STATE.md`.
2. Read the relevant section of `docs/TRENDFORGE_SYSTEM_BRAIN_AND_IMPLEMENTATION_ROADMAP_2026-09-08.md`.
3. Read `docs/TRENDFORGE_ENGINEERING_AUDIT_CROSSWALK_AND_PRESERVED_REQUIREMENTS.md` for the original audit-stage crosswalk and preserved edge cases.
4. For strategy/opportunity work, also read `docs/TRENDFORGE_TRADING_BRAIN_STRATEGY_ENGINE_REFERENCE.md`.
5. Inspect the current owning code and its producer/consumer contracts; do not trust documentation blindly.
6. Identify the affected source, feature, discovery reason, opportunity/strategy, gate, publication and historical-outcome paths.
7. Reproduce the problem on the current revision.
8. Add adversarial tests.
9. Implement the smallest architecture-consistent fix.
10. Run focused and full pinned regression tests.
11. Verify UI/API behavior if exposed.
12. Update current readiness/capability documentation with observed results.

### Future implementation order

Unless a newer evidence-backed audit changes the dependency order, follow the system-brain roadmap:

```text
TF-00 baseline
-> TF-01 event/mandatory gates
-> TF-02 tradability
-> TF-03 execution boundary
-> TF-04 S7/S8 state contract
-> TF-05 canonical assembly
-> TF-06..09 observation/source identity and scheduling
-> TF-10..13 opportunity/discovery/features/profile routing
-> TF-14..19 strategy completion and ranking
-> TF-20..23 incremental publication/UI/outcomes
-> TF-24..25 whole-selector and operational validation
```

Do not jump directly to more indicators, more links, model promotion or live execution while an earlier correctness/lineage dependency remains open.

---

## 7. Document authority rule

For future agents and engineers:

```text
Observed runtime behavior
    > current verified tests/evidence
    > current-state capability summary
    > system-brain intended architecture/roadmap
    > audit crosswalk / preserved requirements
    > historical plans/checkpoints
```

When documentation and runtime disagree, document the mismatch and fix the appropriate layer. Never force runtime behavior to match an obsolete document merely because the document says it is authoritative.
