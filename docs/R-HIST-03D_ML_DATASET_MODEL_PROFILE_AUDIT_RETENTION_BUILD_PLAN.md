# R-HIST-03D — Frozen ML Dataset, Model Version, Strategy Profile, and Audit Retention Build Plan

**Stage:** R-HIST-03D — exact learning/governance memory at ML and strategy-governance producer boundaries  
**Parent plan:** `docs/R-HIST-03_PRODUCER_WIRING_BUILD_PLAN.md`  
**Depends on:** R-HIST-03A + 03B + 03C IMPLEMENTED + TESTED  
**Status:** IMPLEMENTED + TESTED at `fce62874a61e4e2bb6d939bef6d0811e5a266996`; [CI 34496385997](https://github.com/onlyvictus-bit/trendforge/actions/runs/34496385997) PASS; production/live acceptance remains NO. See CURRENT_STATE.md and VALIDATION.md for the acceptance evidence.
**Next after PASS:** R-HIST-03E only  
**Safety ceiling:** research/history/governance only; no automatic model approval, strategy activation, broker authority, or live-order expansion.

---

## 1. Mission

R-HIST-03D makes TrendForge capable of answering, exactly and later:

> What historical population did this dataset contain, what did this model actually learn from, which strategy/profile version interpreted it, which governance evidence was reviewed, and which original evidence existed at each decision time?

The system must not answer that question by rebuilding from whatever the database contains today.

03D therefore extends the protected historical graph from the 03C decision/outcome/revision layer into the learning and governance layer:

```text
ORIGINAL MARKET EVIDENCE
        |
        v
S8 DECISION PUBLICATION
        |
        v
R16 DECISION VERSION
        |
        +--------------------+
        |                    |
        v                    v
     OUTCOME              REVISION
        |                    |
        +----------+---------+
                   |
                   v
          FROZEN ML DATASET
                   |
          +--------+---------+
          |                  |
          v                  v
     MODEL VERSION     STRATEGY PROFILE VERSION
          |                  |
          +--------+---------+
                   |
                   v
             GOVERNANCE/AUDIT
```

A future autonomous research agent may calculate, compare, diagnose and propose improvements, but it must be unable to fabricate provenance, silently substitute corrected data, cherry-pick only winners, or self-approve a model/profile by changing history.

03D is therefore the **learning-memory firewall** between the trading brain and future knowledge.

---

## 2. Why 03D is required for the TrendForge trading brain

TrendForge's architecture requires:

```text
INSTRUMENT != OPPORTUNITY != DECISION VERSION
```

One instrument can have several simultaneous independent opportunities. A frozen training population must preserve those opportunity identities and decision versions independently. Symbol-level collapse is forbidden.

Example:

```text
INFY / 5m / continuation / SHORT / decision D101
INFY / 5m / reversal / LONG      / decision D102
INFY / daily / swing / LONG      / decision D103
```

A training dataset may legitimately contain all three. It must never become merely:

```text
INFY = LONG
```

Likewise, later outcomes do not rewrite the earlier decision inputs. If a source is corrected after a decision, that correction can create a new revision and later dataset version, but the old model must still reconstruct against the old frozen dataset.

This is essential for trustworthy:

- failure-memory learning,
- strategy comparison,
- ML training and evaluation,
- walk-forward validation,
- holdout isolation,
- model governance,
- strategy/profile evolution,
- reproducible research explanations,
- future autonomous research-agent recommendations.

---

## 3. Current code boundary verified before implementation

At the 03C checkpoint, the current repository already contains:

### Historical decision/outcome/revision owners

- `backend/trendforge_api/r16_retention.py`
- `backend/trendforge_api/selection/r16_pit.py`
- `backend/trendforge_api/selection/r16_store.py`
- `backend/trendforge_api/selection/r16_service.py`

These enforce exact S8 parentage, immutable decision/outcome/revision identity, protected evidence roots, separate later observations/revisions, and governed reads.

### Existing R18 governance owners

- `backend/trendforge_api/selection/r18_governance.py`
- `backend/trendforge_api/selection/r18_store.py`

Current R18 already has useful contracts that must be strengthened rather than discarded:

- `ModelManifestV1`
- `ChallengerEvaluationInputV1`
- `ChallengerEvaluationV1`
- `PromotionReviewV1`
- drift/rollback governance
- model, dataset, feature, formula and model hashes
- PIT-status checks
- walk-forward folds and untouched holdout checks
- append-only R18 persistence tables

Current R18 store tables include:

```text
ml_model_registry
ml_evaluation_reports
ml_promotion_reviews
ml_drift_events
```

03D must inspect the current head again before code changes. Strategy-profile and frozen-dataset authoritative producers/tables must be discovered from current runtime code; this plan does not invent a competing owner in advance.

---

## 4. Non-negotiable 03D laws

1. **Exact frozen population, never a query recipe alone.** A dataset is not reproducible merely because its SQL/filter is saved. Its exact selected immutable record identities and hashes must be frozen.
2. **Point-in-time cutoff is mandatory.** Every selected fact must have been available by the declared dataset cutoff under its exact revision lineage.
3. **No latest/current substitution.** A governed dataset/model/profile/audit read may never replace an old parent with a newer decision, outcome, feature, source correction or model.
4. **Complete population.** WAIT, WATCH, REJECT, NO_ENTRY, EXPIRED, AMBIGUOUS, CENSORED, DATA_GAP and other policy-relevant populations remain representable. Training only on entered trades or winners is prohibited unless a purpose-specific dataset explicitly records that transformation and cannot masquerade as the base population.
5. **Opportunity identity is preserved.** Same symbol does not mean same opportunity.
6. **Corrections append.** A corrected source/outcome creates a new revision/dataset/model lineage; it never modifies an old frozen dataset.
7. **Model binary alone is insufficient.** A model version must retain exact dataset, feature/formula/config and governance lineage needed to reconstruct how it was produced and evaluated.
8. **Profile version is immutable.** Strategy semantics, required/optional/prohibited inputs, gate rules, ranking group, market/horizon applicability and model binding cannot change under the same version identity.
9. **Audit evidence is immutable.** Approval, rejection, rollback and review evidence must point to exact artifact versions and predecessor evidence.
10. **Producer-side retention.** Artifact + retention intent share the producer transaction when they share SQLite.
11. **Governed publication waits for retention.** Stored-but-unprotected artifacts remain hidden from governed current/history reads.
12. **Reads do not repair.** GET/UI/reporting paths may verify or block, never generate missing retention or backfill provenance.
13. **Mandatory UNKNOWN never becomes PASS.** Missing chronology, evidence roots, hashes or exact parents blocks governed publication.
14. **No self-approval.** Autonomous agents may propose analyses or candidates but may not bypass existing human/policy governance, PIT approval, model approval or execution boundaries.
15. **No live-order expansion.** Nothing in 03D activates broker/order behavior.

---

## 5. Target retained graph

The minimum graph for a governed model must be reconstructable as:

```text
MODEL VERSION M9
  |
  +-- exact model artifact/hash
  +-- exact training config/code/formula/feature identity where available
  +-- exact evaluation artifact(s)
  +-- exact cost-model version
  +-- exact governance review(s)
  |
  v
FROZEN DATASET D7
  |
  +-- purpose: TRAIN / VALIDATION / TEST / HOLDOUT / RESEARCH
  +-- point-in-time cutoff
  +-- split/fold membership
  +-- inclusion/exclusion policy version
  +-- complete population counts
  |
  v
EXACT POPULATION MEMBERS
  |
  +-- R16 decision version ID/hash
  +-- exact outcome ID/hash when label is available by policy cutoff
  +-- exact revision ID/hash when the dataset intentionally selects that revision
  +-- strategy/opportunity identity
  +-- feature/input manifest hash
  |
  v
S8 + ORIGINAL MARKET EVIDENCE ROOTS
```

A model explanation must be able to walk down this graph without asking for the newest record.

---

## 6. Stage decomposition

03D is implemented in the following internal order. The implementation agent must not skip a substage because a later artifact appears easier.

```text
D0  ownership/schema reconnaissance
 -> D1 frozen dataset manifest contract
 -> D2 PIT population closure
 -> D3 feature/evidence transitive closure
 -> D4 model-version retention
 -> D5 strategy-profile retention
 -> D6 governance/audit retention
 -> D7 governed reads + replay/recovery
 -> D8 migration/legacy boundary + acceptance gate
```

### D0 — ownership and schema reconnaissance

Before editing code:

1. inspect the current PR head;
2. identify the exact writer for every R18 table;
3. identify whether a frozen dataset manifest already has a canonical store;
4. identify current strategy/profile configuration/version owners;
5. identify current governance review, evaluation and drift write paths;
6. map caller -> producer -> table/store -> current read path;
7. record which stores share the research SQLite transaction;
8. identify existing tests and migrations;
9. identify any compatibility/read paths that currently persist artifacts;
10. create failing tests before implementation.

**D0 stop rule:** if authoritative ownership cannot be proven, do not invent a parallel store. Record the ambiguity and stop the affected substage.

---

## 7. D1 — Frozen ML dataset manifest contract

03D should introduce or strengthen one immutable frozen-dataset manifest rather than storing only `dataset_hash` as an opaque string.

Exact field names may reuse current contracts, but the semantic content must include at least:

```text
FrozenDatasetManifest
- dataset_id
- dataset_version
- dataset_hash
- schema_version
- purpose
- created_at
- pit_cutoff
- population_policy_id/version
- label_policy_id/version
- feature_manifest_id/hash
- formula_set_hash/version
- cost_model_version when applicable
- member_count
- member_manifest_hash
- split/fold manifest
- state distribution
- outcome distribution
- exclusion-reason distribution
- source/evidence root digest
- parent/revision policy
- code/config digest when the existing build path can prove it
- retention/publication state
```

### Dataset member identity

A member must retain enough exact identity to distinguish independent opportunities and revisions. Example conceptual shape:

```text
DatasetMember
- member_id/hash
- instrument/contract identity
- opportunity_id
- strategy/profile version
- timeframe
- direction
- setup episode
- decision_version_id/hash
- decision_time
- data_cutoff
- selected_outcome_id/hash | null
- selected_revision_id/hash | null
- label availability cutoff
- feature/input manifest hash
- exact evidence roots
- split/fold membership
- inclusion reason
```

The dataset hash must be derived from canonical immutable manifest material, not creation order, DB row IDs that can vary by environment, or browser time.

### Frozen means frozen

Once D7 exists:

```text
D7 hash H1
```

later creation of O2/R2/new features must not cause D7 to resolve differently.

A corrected population becomes:

```text
D8 hash H2
```

with explicit relationship to D7 if the current revision model supports it.

---

## 8. D2 — Point-in-time population closure

A dataset builder must select from **governed, verified historical records**, not raw current tables.

For every candidate member:

1. verify DECISION_VERSION publication;
2. verify exact S8 parent and evidence closure through the 03C verifier;
3. verify outcome/revision publication if used;
4. verify that selected outcome/revision was eligible under the dataset's label/knowledge cutoff;
5. preserve the exact selected version;
6. reject records whose lineage cannot be proven.

### No future-label leakage

A dataset may intentionally use later outcomes to label earlier decisions, but the policy must distinguish:

```text
DECISION KNOWLEDGE CUTOFF
```

from:

```text
LABEL OBSERVATION WINDOW / DATASET BUILD CUTOFF
```

The later outcome must never be inserted into the earlier decision features.

### Complete-population guard

The builder must report counts for at least the relevant populations available in the selected scope, including:

```text
CONFIRMED
WATCH
WAIT
REJECT
NO_ENTRY
EXPIRED
TARGET_HIT
STOP_HIT
AMBIGUOUS
CENSORED
DATA_GAP
NO_GEOMETRY
INVALIDATED_BEFORE_ENTRY
```

Exact enumerations must follow the current contracts at implementation time.

A training transformation may exclude classes only when:

- the exclusion policy is explicit/versioned;
- exclusion counts/reasons are frozen;
- the resulting artifact cannot be mistaken for the base historical population;
- evaluation includes selection-bias checks appropriate to the model purpose.

---

## 9. D3 — Feature and evidence transitive closure

A frozen dataset must not point only to decision IDs while allowing its original inputs to disappear.

For each member, protection must close transitively through:

```text
dataset member
 -> decision/outcome/revision publication
 -> S8 parent publication
 -> original feature/input manifest
 -> original market-data object/content hashes
 -> retained market evidence object roots
```

Where a PIT feature manifest does not yet exist as a first-class object, implementation must either:

- extend the current immutable decision/dataset contract to freeze the exact feature/input material and hash it, or
- introduce one canonical feature-manifest owner after D0 proves no existing canonical owner.

It must never reconstruct an old feature vector by rerunning today's formula against today's corrected history and call it original.

### Semantically different features stay different

The feature identity must preserve relevant semantics such as:

```text
feature ID + version
parameters
timeframe/session
input vintage digest
corporate-action/roll policy
data cutoff
value/source timestamp
comparison universe/cohort version for cross-sectional features
```

This protects the trading brain from accidentally learning that daily RVOL, same-time intraday RVOL, or two different VWAP semantics were the same feature.

---

## 10. D4 — MODEL_VERSION retention

Current `ModelManifestV1` already contains model ID/version, market/horizon, dataset hash, feature-set hash, formula-set hash and model hash. 03D must strengthen the publication graph so these hashes are not unresolvable labels.

A governed model version must retain/prove:

```text
model_id
model_version
model_hash / artifact hash
market
horizon
purpose
exact training dataset manifest ID/hash
exact evaluation/validation/holdout dataset IDs/hashes where applicable
feature-set and formula-set identity
training configuration/hyperparameters/seeds when current producer owns them
code/build identity when current producer can prove it
cost-model version
evaluation artifact ID/hash
governance state
created_at
```

### Model reference law

`MODEL_VERSION` retention must be registered through the existing HistoricalRetentionAuthority/outbox pathway.

A model cannot be governed-public if:

- the dataset hash exists only as an unresolvable string;
- its frozen dataset publication is missing or blocking;
- the model hash does not match its immutable manifest/artifact;
- evaluation points at a different dataset version;
- the model attempts to substitute a newer dataset/model binary under the old ID;
- required training/evaluation evidence is no longer protected.

### Preserve current R18 safety

Current R18 requires PIT approval before human promotion and does not automatically promote. 03D must not weaken that ceiling.

`MODEL_NOT_APPROVED` remains the safe result whenever existing governance prerequisites are not satisfied.

---

## 11. D5 — STRATEGY_PROFILE retention

The strategy/profile version is part of the meaning of every opportunity and model interpretation. It must not be mutable configuration hiding behind one profile name.

After D0 identifies the authoritative current profile owner, freeze and protect a version containing at least the applicable semantics:

```text
profile_id
profile_version
strategy/evaluator ID + version
market/instrument class
holding horizon
timeframe/setup/direction applicability
REQUIRED_TO_CALCULATE inputs
REQUIRED_TO_QUALIFY inputs
OPTIONAL_CONTEXT inputs
PROHIBITED_FOR_THIS_CONDITION inputs
relative-strength contract
event/tradability/liquidity gate policy
ranking group
cost/risk assumptions
model version binding if applicable
publication path
activation/research ceiling
created_at / valid_from
profile content hash
```

### Profile version law

Changing any semantic input/gate/ranking/model binding creates a new profile version.

Never mutate:

```text
PRF-X v1
```

and then claim old decisions used the new v1 meaning.

The retained profile must preserve the trading-brain rule that discovery does not own strategy direction and that unrelated strategies can have different required evidence.

---

## 12. D6 — AUDIT/governance retention

Current R18 already persists promotion reviews with evidence hashes and predecessor-chain fields. 03D must connect these and equivalent governance artifacts to `AUDIT` retention.

An immutable audit/review record must bind to exact:

```text
review/audit ID
reviewed artifact type + ID/version/hash
model/dataset/profile/evaluation IDs/hashes
previous review/record hash where chained
decision: approve/reject/demote/rollback/etc.
reason codes/text
reviewer/actor identity when current contract requires it
review time
evidence hash/root
governance policy version
resulting state
```

Drift and rollback evidence must also remain reconstructable where it changes governance state.

### Audit cannot manufacture authority

An AUDIT record records governance; it does not create data truth.

A human or autonomous agent saying "approve" must still fail if:

- PIT is not approved;
- the exact dataset/model/profile graph is not protected;
- evaluation evidence is missing/tampered;
- the current governance policy prohibits promotion.

---

## 13. D7 — Transaction, publication, replay and governed reads

03D must reuse the 03A–03C publication architecture rather than create a second retention mechanism.

Preferred same-DB write path:

```text
BEGIN IMMEDIATE
  INSERT immutable dataset/model/profile/audit artifact
  INSERT immutable artifact-retention link
  INSERT deterministic retention outbox PENDING
COMMIT

post-commit worker:
  verify exact parent graph
  register with HistoricalRetentionAuthority
  mark outbox APPLIED
  mark/allow governed publication
```

### Crash semantics

```text
crash before COMMIT
 -> artifact and retention intent both absent

crash after COMMIT before authority registration
 -> stored internal artifact remains hidden
 -> PENDING survives
 -> worker resumes

register succeeds, crash before APPLIED acknowledgement
 -> replay exact deterministic reference
 -> authority idempotency converges

verification fails
 -> FAILED_BLOCKING / equivalent blocking state
 -> governed publication prohibited
```

### Read law

Governed reads must verify the retained graph and fail closed if it is broken.

They must never:

- enqueue missing retention,
- register missing references,
- repair hashes,
- pick a newer parent,
- rebuild a frozen dataset,
- backfill legacy rows.

Explicit producer/admin recovery commands may resume deterministic known intents. Reads may not.

---

## 14. D8 — Migration and legacy boundary

03D should use additive migration(s). Exact migration numbers are assigned only after inspecting the current branch migration sequence.

Rules:

- no destructive rewrite of R18 migration `0014`;
- no UPDATE/DELETE-based conversion of old immutable artifacts;
- new indexes/triggers/links may be additive;
- old R18 records without exact protected dataset lineage remain stored but are not automatically upgraded to governed 03D history;
- current/latest hashes must never be stamped onto old records;
- any historical repair requires separately proven original provenance.

Legacy states must be reported explicitly, for example:

```text
LEGACY_UNGOVERNED
LEGACY_LINEAGE_UNVERIFIABLE
PENDING_RETENTION
PUBLISHED
FAILED_BLOCKING
```

Use actual current state enums/contracts rather than inventing user-visible status names if existing equivalents already exist.

---

## 15. Autonomous research-agent contract

03D is designed so a future high-autonomy TrendForge research agent can reason safely from memory.

### Allowed autonomous behavior

The agent may:

- compare frozen datasets;
- identify failure clusters;
- propose feature/strategy changes;
- build a new candidate dataset version;
- train/evaluate a challenger under approved offline workflow;
- explain why a model/profile changed;
- identify missing populations or leakage risk;
- trace every conclusion to immutable IDs/hashes;
- recommend a new model/profile for human/policy review.

### Forbidden autonomous behavior

The agent may not:

- rewrite history to improve performance;
- substitute latest data for missing old evidence;
- delete losers/WAIT/REJECT/NO_ENTRY examples to make a model look better;
- merge independent same-symbol opportunities;
- relabel ambiguity as loss/win without policy;
- approve its own model by bypassing governance;
- change profile semantics under the same version;
- invent a source timestamp, feature hash or evidence root;
- infer that a green test means live profitability;
- activate broker execution.

### Reasoning requirement

Every high-level claim such as:

```text
"reversal model improved because failed-breakdown cases now use feature X"
```

must be traceable to:

```text
model version
 -> evaluation
 -> frozen dataset version
 -> exact opportunity population
 -> exact decisions/outcomes/revisions
 -> exact evidence roots
```

If the graph cannot be proven, the correct autonomous answer is **UNKNOWN/BLOCKED**, not a confident guess.

---

## 16. Test-first adversarial matrix

Tests must be written/observed failing before corresponding implementation where behavior is new.

### Dataset identity and population

1. exact governed R16 parent accepted;
2. missing decision publication rejected;
3. wrong decision hash/version rejected;
4. tampered decision/outcome/revision rejected;
5. newer decision cannot replace selected old decision;
6. later source correction cannot mutate old dataset;
7. later outcome revision cannot alter old dataset membership;
8. same symbol with independent opportunities remains separate;
9. duplicate member identity fails deterministically;
10. member ordering does not create nondeterministic dataset identity;
11. exact replay returns same dataset/reference;
12. changed population creates a new hash/version;
13. WAIT/REJECT/NO_ENTRY/EXPIRED retained in population accounting;
14. AMBIGUOUS/CENSORED/DATA_GAP remain explicit;
15. illegal winner-only/entered-only base population fails validation;
16. exclusion policy/counts are frozen.

### PIT chronology/leakage

17. feature/source available after decision cutoff cannot enter decision feature vector;
18. label observed later may label under explicit label window but never enter decision features;
19. corrected vintage after PIT cutoff cannot substitute original;
20. unproven availability time fails closed;
21. chronological train/test/holdout violation rejected;
22. holdout overlap/reuse rejected according to governance contract.

### Feature/evidence closure

23. missing feature manifest/root blocks dataset publication;
24. altered feature semantics/hash blocks replay;
25. deleted/tampered market evidence detected;
26. current recalculation cannot repair old feature vector;
27. transitive cleanup protection survives.

### Model version

28. exact frozen dataset accepted;
29. opaque/unresolvable dataset hash blocks governed model publication;
30. wrong dataset version/hash rejected;
31. model artifact/hash mismatch rejected;
32. evaluation dataset mismatch rejected;
33. newer dataset cannot replace original model parent;
34. model replay is idempotent;
35. model cannot auto-promote when current governance ceiling blocks it.

### Strategy profile

36. exact immutable profile accepted;
37. same profile ID/version with changed gate/input/model material rejected;
38. new profile semantics require new version;
39. wrong model binding rejected;
40. required/optional/prohibited input classifications retained;
41. one profile cannot overwrite another independent strategy profile.

### Audit/governance

42. exact review/evidence chain accepted;
43. wrong predecessor review hash rejected;
44. tampered evidence hash rejected;
45. review cannot repoint to another model/dataset/profile;
46. approval rejected when PIT/model prerequisites fail;
47. drift/rollback lineage remains reconstructable.

### Transaction/recovery/read purity

48. failure before commit leaves no artifact/outbox;
49. crash after commit leaves hidden replayable artifact;
50. authority success then crash before APPLIED replays same reference;
51. authority failure leaves artifact hidden;
52. read/get/list performs zero retention writes;
53. cleanup cannot remove referenced evidence;
54. frozen dataset reload is byte/hash equivalent after later corrections;
55. legacy unprotected records are not auto-backfilled;
56. database lock/storage failure never claims publication complete.

This list is minimum coverage, not a cap.

---

## 17. Observability required by 03D

Expose or make queryable enough state to diagnose:

```text
frozen_dataset_count
frozen_dataset_blocking_count
model_version_retention_count
strategy_profile_retention_count
audit_retention_count
unresolved_parent_count
legacy_ungoverned_count
population_state_distribution
population_outcome_distribution
dataset_lineage_verification_failures
model_lineage_verification_failures
profile_lineage_verification_failures
audit_chain_verification_failures
```

Do not expose a metric as proof of profitability. These are integrity/governance metrics.

---

## 18. Acceptance gate for R-HIST-03D

03D may be declared **IMPLEMENTED + TESTED** only when all are true:

1. D0 ownership map completed against current code;
2. frozen dataset manifest exists and is immutable;
3. exact PIT population membership is frozen;
4. non-trade/negative/ambiguous populations are explicitly preserved;
5. dataset evidence closure reaches protected 03C/S8/original evidence roots;
6. MODEL_VERSION uses exact resolvable dataset/evaluation lineage;
7. STRATEGY_PROFILE versions are immutable and retained;
8. AUDIT/governance artifacts are retained with exact evidence/predecessor chains;
9. artifact + retention intent transaction behavior is proven;
10. governed reads verify but never repair;
11. replay/idempotency and crash recovery pass;
12. legacy/unverifiable rows remain fail-closed;
13. focused new 03D adversarial tests pass;
14. existing 03A/B/C retention tests pass;
15. full backend regression passes in the pinned/CI environment;
16. Ruff passes;
17. Python compilation passes;
18. frontend tests pass if shared API/contracts/docs affect frontend behavior;
19. Mypy is compared honestly against the current known baseline and introduces no unexplained new diagnostics; a non-blocking Mypy job is not called a pass;
20. exact final PR-head GitHub CI is observed and recorded.

**STOP:** do not begin 03E implementation unless this gate passes.

---

## 19. Handoff to 03E

03D must leave 03E with a machine-enumerable set of governed producer classes and exact publication records.

Expected governed classes after 03D include, subject to D0 verification of current ownership:

```text
DECISION_VERSION
OUTCOME
REVISION
ML_DATASET
MODEL_VERSION
STRATEGY_PROFILE
AUDIT
```

03E will not redesign these producers. It will prove that every mandatory governed artifact actually has the required exact APPLIED retention relationship and that no unexplained orphan exists.

---

## 20. One-stretch execution rule

The user intends to build 03D -> 03E -> 03F in one continuous engineering run. That is allowed only with hard gates:

```text
03D RED TESTS
 -> IMPLEMENT 03D
 -> FOCUSED + FULL GATE

PASS
 -> start 03E

FAIL
 -> STOP
 -> record exact failure/evidence
 -> do not begin 03E
```

This is autonomous sequential execution, not blind continuation.

---

## 21. Final 03D definition

03D is complete when TrendForge can truthfully say:

> For this dataset/model/profile/audit record, I can prove exactly which historical decisions, outcomes, revisions, feature semantics and original evidence it depended on, I can reconstruct that graph after newer corrections exist, and I cannot silently rewrite it to make later research look better.

Until that statement is mechanically verified, `R-HIST-03D = NOT COMPLETE`.
