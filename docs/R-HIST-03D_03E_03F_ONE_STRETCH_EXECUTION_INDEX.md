# R-HIST-03D / 03E / 03F — One-Stretch Execution Index

**Parent authority:** `docs/R-HIST-03_PRODUCER_WIRING_BUILD_PLAN.md`  
**Purpose:** navigation and hard-gate execution contract for completing the remaining R-HIST-03 stages without redesigning between stages.  
**Status:** plans ready; 03D/03E/03F runtime implementation not started at creation of this index.

## Required order

```text
R-HIST-03A  IMPLEMENTED + TESTED
R-HIST-03B  IMPLEMENTED + TESTED
R-HIST-03C  IMPLEMENTED + TESTED
        |
        v
R-HIST-03D  frozen ML datasets / models / profiles / audits
        |
        | PASS GATE ONLY
        v
R-HIST-03E  producer registry / coverage / orphan reconciliation
        |
        | PASS GATE ONLY
        v
R-HIST-03F  crash / concurrency / tamper / replay / golden acceptance
        |
        | PASS GATE ONLY
        v
FULL R-HIST-03 AGGREGATE GATE
        |
        | PASS ONLY
        v
R-HIST-04 archival implementation may begin
```

## Detailed build contracts

### R-HIST-03D

`docs/R-HIST-03D_ML_DATASET_MODEL_PROFILE_AUDIT_RETENTION_BUILD_PLAN.md`

Mission: make every frozen training/evaluation dataset, model version, strategy-profile version and governance/audit record reconstructable from exact point-in-time decisions, outcomes, revisions, feature semantics and original evidence roots.

Key safety result:

```text
future research/model learning
 -> exact frozen historical graph
 -> never latest/current substitution
 -> complete negative/non-trade population preserved
 -> no model/profile self-approval
```

### R-HIST-03E

`docs/R-HIST-03E_PRODUCER_COVERAGE_RECONCILIATION_BUILD_PLAN.md`

Mission: create a machine-enumerable producer registry and prove every mandatory governed artifact has exact APPLIED retention with zero unexplained orphan artifacts/references and intact transitive lineage.

Key acceptance result:

```text
mandatory coverage ratio = 1.0
unexplained orphan artifacts = 0
unexplained orphan references = 0
broken transitive lineage = 0
```

### R-HIST-03F

`docs/R-HIST-03F_FAULT_INJECTION_CONCURRENCY_GOLDEN_ACCEPTANCE_BUILD_PLAN.md`

Mission: prove the entire memory system fails closed and recovers correctly when transactions crash, workers race, leases expire, authority success is uncertain, bytes are tampered, cleanup races retention, or reads occur during recovery.

Key safety result:

```text
uncertain/corrupt/partial state
 -> PENDING / BLOCKED / recoverable
 -> NEVER false published history
 -> NEVER false 100% coverage
 -> NEVER future-data repair
```

## One-stretch execution law

The remaining stages may be executed continuously in one engineering session, but progression is autonomous only across a passed gate:

```text
03D RED TESTS
 -> IMPLEMENT
 -> FOCUSED TESTS
 -> FULL REGRESSION / RUFF / COMPILE / FRONTEND IF AFFECTED
 -> MYPY BASELINE COMPARISON
 -> EXACT PR-HEAD CI

PASS -> 03E
FAIL -> STOP AT 03D

03E RED TESTS
 -> IMPLEMENT
 -> SAME GATE DISCIPLINE

PASS -> 03F
FAIL -> STOP AT 03E

03F RED/FAULT TESTS
 -> IMPLEMENT
 -> GOLDEN / CONCURRENCY / TAMPER / CLEANUP / REPLAY MATRIX
 -> SAME FULL GATE DISCIPLINE

PASS -> FULL R-HIST-03 aggregate gate
FAIL -> STOP AT 03F
```

No stage may be marked complete from code presence alone.

## Trading-brain relationship

R-HIST is the trustworthy notebook for the future multi-strategy opportunity engine. It does not replace the trading brain and it does not decide LONG/SHORT itself.

```text
TRADING BRAIN
 discovery -> opportunity -> strategy evaluation -> decision
                         |
                         v
                    R-HIST MEMORY
                         |
                         v
            outcomes / frozen datasets / ML
                         |
                         v
              research improvement loop
```

The memory layer must preserve the architecture rule:

```text
INSTRUMENT != OPPORTUNITY != DECISION VERSION
```

It must support simultaneous independent opportunities such as continuation SHORT, reversal LONG and swing LONG for the same instrument without collapse.

## Autonomous research-agent safety law

A future high-autonomy research agent may inspect, compare, diagnose and propose new datasets/models/profiles only when the historical graph is verified.

```text
verified memory -> analysis may proceed under other gates
broken/unknown memory -> BLOCK / UNKNOWN
```

It may never:

- invent historical provenance;
- replace old evidence with latest/current data;
- remove losing/non-trade history to improve apparent performance;
- change old decision/profile/model semantics under the same version;
- reduce the coverage denominator to hide missing retention;
- self-approve a model or strategy;
- activate broker execution.

## Capability boundary

Completion of all three plans plus the full R-HIST-03 gate means only that historical retention producer wiring is implemented and tested.

It does **not** itself mean:

```text
LIVE-DATA-VERIFIED
PIT_APPROVED
MODEL_APPROVED
STRATEGY_ACTIVATED
PRODUCTION_ACCEPTED
EXECUTION_AUTHORIZED
```

Those remain separate TrendForge gates.
