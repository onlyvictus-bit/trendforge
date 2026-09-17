# R-HIST-03D Implementation Safety and Root-Cause Repair Plan

Status: implementation contract, not completion evidence.

## Scope

This plan repairs the R-HIST-03D semantic hashing and typed-retention defects without changing R-HIST-03A/03B/03C identities, market cleanup behavior, model authority, strategy authority, automatic promotion, or broker/execution authority.

The active implementation branch is `feat/rhist03-producer-wiring`. R-HIST-03D remains IN PROGRESS until exact-head CI and all stage gates pass. R-HIST-03E and R-HIST-03F remain gated.

## Non-negotiable invariants

1. `INSTRUMENT != OPPORTUNITY != DECISION VERSION` remains unchanged.
2. Market-object `content_hash` keeps its existing meaning and legacy event identity.
3. Typed 03D semantic artifacts use a separate `artifact_hash` identity domain.
4. Legacy payloads omit `artifactHash` when unused so old `lineage_digest`, `event_id`, and `reference_id` values remain byte-for-byte stable.
5. Existing historical rows are never rewritten to invent provenance.
6. Reads never repair, backfill, supersede, or bless current/latest data.
7. Mandatory unknown/missing/tampered evidence fails closed.
8. Pure builders remain side-effect free; authoritative parent proof belongs at persistence/finalization/governed-read boundaries.
9. No live-order, strategy-activation, model-promotion, or trading-authority expansion.

## Root causes being repaired

### A. Pre-validation semantic hashing

`r18_history.py` currently uses `_normalized_material(... model_construct ...)`. `model_construct()` bypasses normal Pydantic validation, so nested raw dictionaries/defaults/coercions can be hashed differently from the fully validated object later verified by model validators. The immediate symptom is `DATASET_MEMBER_HASH_MISMATCH`, but the same pattern is reused by dataset manifests, governed models, strategy profiles, and governance audit records.

Repair law: define validated semantic material contracts without self-referential identity fields. Builders and validators must both hash the same fully validated normalized material. Eliminate `model_construct()` from semantic identity generation.

### B. Typed semantic hashes routed through market `content_hash`

R18 currently stages ML_DATASET / MODEL_VERSION / STRATEGY_PROFILE / AUDIT semantic hashes as `RetentionEvidenceIntent.content_hash`. HistoricalRetentionAuthority interprets `content_hash` as a market-data-object SHA-256 and queries `market_data_objects`, causing valid semantic artifacts to fail registration.

Repair law: keep `content_hash` for market evidence and add a separate typed artifact identity: `artifact_id + artifact_version + artifact_hash`.

### C. Stored verification and governed-read gaps

The current stored verifier checks serialized checksum/index alignment for only dataset/model/profile and does not reconstruct every typed semantic model. Governed dataset reads trust `publication_state='APPLIED'` too much and there is no complete 03D finalization lifecycle proving local artifact + outbox + authority + parents before exposing governed history.

Repair law: split local semantic verification from governed verification, then add an explicit crash-safe finalizer.

## Revised implementation sequence

### Phase 0 - inventory / STOP gate

Before migration or supersession logic, inspect 03D artifacts across:
- `ml_frozen_datasets`
- `ml_governed_model_versions`
- `strategy_profile_versions`
- `governance_audit_records`
- `r18_retention_links`
- `historical_retention_outbox`
- `historical_retention_references`

Classify typed 03D rows as PENDING, FAILED_BLOCKING, or APPLIED.

If a pre-fix typed 03D semantic artifact is genuinely APPLIED, stop and require an explicit compatibility/migration decision. Do not silently rewrite it.

For pre-production PENDING/FAILED_BLOCKING artifacts, preserve the old event and support an explicit controlled supersession path to a corrected typed event. Never mutate the old immutable event in place.

### Phase 1 - freeze semantic identity contract

Normalize:
- SHA-256 text to lowercase before hashing/verification.
- timezone-aware datetimes to UTC.
- collection ordering where order is semantically irrelevant.
- nested semantic values to an explicitly permitted JSON-value domain.

Reject non-finite floats (`NaN`, `Infinity`, `-Infinity`), arbitrary Python objects, unsupported keys, and any value whose semantic serialization is ambiguous. Do not rely on `default=str` for semantic identity.

### Phase 2 - validated material models

Replace `_normalized_material()` / `model_construct()` hashing for all identity-bearing 03D models:
- `FrozenDatasetMemberV1`
- `FrozenDatasetManifestV1`
- `GovernedModelVersionV1`
- `StrategyProfileVersionV1`
- `GovernanceAuditRecordV1`

Use private validated material contracts that contain all semantic fields except the computed identity field(s). Both builder and validator must call the same material validation/canonical-hash path.

### Phase 3 - persistence-boundary revalidation

Do not trust an already-instantiated frozen model blindly. Before persistence, dump to a fresh Python structure and perform full validation/semantic recomputation. This protects against nested mutable values or non-validating update paths.

### Phase 4 - preserve legacy retention identity

Extend `RetentionEvidenceIntent` additively with `artifact_hash: str | None = None`.

`canonical_payload()` must include `artifactHash` only when non-null. `lineage_digest` must be derived from the canonical payload minus `createdAt`, preserving the exact old identity when `artifact_hash` is absent.

Freeze this legacy regression anchor:
- digest `b52b2e1df11b2cec05eba1f6bf5402e2739d3d87ec9d3b4143aea0b55d39ad87`
- event `rhist03:b52b2e1df11b2cec05eba1f6bf5402e2739d3d87ec9d3b4143aea0b55d39ad87`
- reference `decision_version:b52b2e1df11b2cec05eba1f6bf5402e2739d3d87ec9d3b4143aea0b55d39ad87`

### Phase 5 - additive schema migration

Add nullable columns only; never rewrite old rows:
- `historical_retention_outbox.artifact_hash`
- `historical_retention_references.artifact_id`
- `historical_retention_references.artifact_version`
- `historical_retention_references.artifact_hash`

Use idempotent column checks. Schema status must verify required tables and required columns, not only migration markers.

Never backfill `artifact_hash = content_hash`.

### Phase 6 - typed HistoricalRetentionAuthority

Market mode stays unchanged:
- `content_hash`
- `run_id`
- `trading_date`
- market manifest/object validation

Typed semantic mode requires exactly:
- `reference_type`
- `artifact_id`
- `artifact_version`
- `artifact_hash`

Reject ambiguous mixed market + semantic locators.

Exact type mapping:
- ML_DATASET -> `ml_frozen_datasets(dataset_id,dataset_version,dataset_hash)`
- MODEL_VERSION -> `ml_governed_model_versions(model_id,model_version,model_hash)`
- STRATEGY_PROFILE -> `strategy_profile_versions(profile_id,profile_version,content_hash)`
- AUDIT -> `governance_audit_records(audit_id,'1',record_hash)` under the current synthetic audit-version contract

For typed registration verify the exact row, serialized-payload checksum, parsed payload semantic hash, and full typed semantic model validation before inserting the authority reference.

### Phase 7 - R18 staging

For ML_DATASET / MODEL_VERSION / STRATEGY_PROFILE / AUDIT:
- `content_hash=None`
- `artifact_hash=<semantic hash>`

Do not create fake `market_data_objects` rows for semantic artifacts.

### Phase 8 - local semantic verifier

Create one local verifier that may run while the artifact is PENDING_RETENTION. It verifies:
- stored payload checksum
- JSON parse
- exact Pydantic type reconstruction
- semantic-hash recomputation
- indexed id/version/hash equality
- dataset member materialization against canonical manifest members
- audit support

This verifier must not require retention APPLIED; otherwise retention registration would become circular.

### Phase 9 - pre-fix 03D event handling

Preserve old PENDING/FAILED_BLOCKING events. Do not mutate their payloads or locators.

Support an explicit, narrowly scoped corrected event for typed 03D artifacts only when the previous event is non-APPLIED and the current artifact passes local semantic verification. Preserve evidence of the superseded failed/pending event.

Any pre-fix APPLIED typed event is a STOP condition requiring separate review.

### Phase 10 - upstream parent proof

A frozen dataset may be locally syntactically valid but still historically false. Before governed publication, every member must prove its exact authoritative history:
- decision version id/hash resolves to exact governed R16 publication
- optional outcome id/hash resolves to exact governed R16 outcome
- optional revision id/hash resolves to exact governed R16 revision and predecessor chain
- evidence roots match protected S8/R16 lineage
- decision-time known/available-at rules hold
- later corrections/latest data cannot substitute earlier known evidence
- feature/formula/input identities are exact and not inferred from current data

Pure builders remain database-independent; this proof belongs at persistence/finalization/governed-read boundaries.

### Phase 11 - downstream dependency proof

MODEL_VERSION must prove exact APPLIED + verified training/evaluation/holdout datasets by id + version + semantic hash.

STRATEGY_PROFILE with a model binding must prove exact APPLIED + verified model by id + version + hash.

AUDIT must prove its reviewed artifact, dataset/model/profile/evaluation dependencies as declared by the audit contract, plus predecessor audit integrity.

### Phase 12 - crash-safe finalizer

Implement an idempotent finalizer:
1. load local artifact/link
2. local semantic verification
3. dispatch typed retention event
4. require outbox APPLIED
5. verify exact authority reference
6. prove authoritative parents
7. in one guarded local transaction update both `r18_retention_links.publication_state` and artifact `publication_state` from PENDING_RETENTION to APPLIED

Crash before commit leaves both local states pending. Replay repeats verification and safely completes. State disagreement fails closed.

### Phase 13 - governed read

Never return an artifact just because its state string says APPLIED. Governed read must re-verify:
- local semantic integrity
- child member integrity where applicable
- APPLIED local link
- exact APPLIED outbox event and payload
- exact authority reference
- exact upstream/downstream parent graph

Reads remain pure and never repair/backfill.

### Phase 14 - regression and acceptance

Required groups:
1. semantic hashing and canonicalization attacks
2. legacy 03A/03B/03C fixed identity regression
3. fresh/old/partial schema migration and idempotency
4. typed retention success/failure cases
5. finalizer crash/replay/state-split cases
6. upstream R16/S8 historical truth and known-at attacks
7. downstream dataset/model/profile/audit dependency attacks
8. full 03A/03B/03C regression suite
9. full backend tests
10. Ruff
11. compileall
12. normalized Mypy delta with no new 03D diagnostics
13. frontend CI
14. exact-head CI inspection

Only after all gates pass may R-HIST-03D be marked PASS. Only then may R-HIST-03E begin.

## Hard acceptance laws

- No existing market retention event/reference identity changes when `artifact_hash` is absent.
- No typed semantic artifact hash appears in `RetentionProtectionSet.content_hashes`.
- No fake market object is created for a dataset/model/profile/audit hash.
- No current/latest data repairs historical lineage.
- No APPLIED artifact is exposed when bytes, semantic identity, retention evidence, or parents are missing/tampered.
- No failed registration creates an authority reference.
- Artifact + initial outbox staging is atomic.
- Final APPLIED state transition is crash-safe/idempotent.
- Old pre-fix events are preserved, never silently rewritten.
- R-HIST-03A/03B/03C behavior remains unchanged.
- Model/strategy/execution authority remains unchanged.

## Stage status

R-HIST-03A: preserve
R-HIST-03B: preserve
R-HIST-03C: preserve
R-HIST-03D: IN PROGRESS
R-HIST-03E: GATED
R-HIST-03F: GATED
LIVE-DATA-VERIFIED: NO
PRODUCTION-ACCEPTED: NO
