# Historical Retention Build Index

**Purpose:** navigation and implementation-status index for TrendForge historical evidence retention, point-in-time reconstruction, backtesting and future ML memory.

**Governing rule:** **Delete copies, not history.** Age determines storage tier; durable evidence references determine deletability.

## Read these first

1. `docs/CURRENT_STATE.md` — current implementation/readiness snapshot.
2. `docs/HISTORICAL_DATA_RETENTION_AND_ML_MEMORY_PLAN.md` — full architecture, safety invariants and R-HIST-01 through R-HIST-07 roadmap.
3. `backend/trendforge_api/historical_retention.py` — retention authority, policy, immutable references and fail-closed protection resolution.
4. `backend/trendforge_api/market_data_store.py::MarketDataStore.cleanup_retention` — real destructive cleanup path wired by R-HIST-02.
5. `backend/tests/test_retention_evidence_safety.py` — authority and lineage-integrity tests.
6. `backend/tests/test_retention_cleanup_integration.py` — destructive-cleanup integration/adversarial tests.

## Stage status

| Stage | Scope | Status |
|---|---|---|
| R-HIST-01 | retention authority, HOT/WARM/COLD classification, durable reference types, immutable reference identity, transitive protection, fail-closed validation | IMPLEMENTED + TESTED on prior exact-head CI |
| R-HIST-02 | wire protection into real cleanup; protect referenced date/run/hash; re-check before deletion; adversarial cleanup tests | IMPLEMENTED; final exact-head CI pending |
| R-HIST-03 | automatically register references from decision/outcome/revision/ML/model/profile/audit producers | NOT STARTED |
| R-HIST-04 | HOT -> WARM -> COLD/archive movement and hash-verified restore | NOT STARTED |
| R-HIST-05 | frozen point-in-time ML dataset builder + leakage audit | NOT STARTED |
| R-HIST-06 | full opportunity/outcome/failure memory for WAIT/WATCH/REJECT/CONFIRMED/no-entry/expired/etc. | NOT STARTED |
| R-HIST-07 | real-data reconstruction, PIT replay/backtest, leakage tests, shadow verification and production acceptance | NOT STARTED |

## Safety boundaries

- The old five-completed-trading-day cleanup setting is not allowed to override an active durable evidence reference after R-HIST-02.
- Five days is **not** the final desired retention lifecycle. Tier movement/archive remains R-HIST-04.
- A durable `reference_id` cannot be silently repointed to different evidence.
- Missing protected date/run/hash lineage fails closed.
- `dry_run=True` remains the cleanup default.
- Retention work grants no broker/order/live-execution authority.
- Unit/CI success does not equal LIVE-DATA-VERIFIED or PRODUCTION-ACCEPTED.

## Next coding stage after R-HIST-02 verification

R-HIST-03: producer wiring. A historical-memory system is not autonomous until every immutable decision, outcome, revision, dataset/model/profile evaluation and audit artifact automatically emits the correct retention references. Manual references are a safety mechanism, not the finished intelligence loop.
