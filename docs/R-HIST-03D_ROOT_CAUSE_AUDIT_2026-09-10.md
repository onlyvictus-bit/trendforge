# R-HIST-03D Root-Cause Audit — Semantic Hashing + Typed Retention

**Date:** 2026-09-10  
**Repository:** `onlyvictus-bit/trendforge`  
**Branch audited:** `feat/rhist03-producer-wiring`  
**Audited head before this note:** `47828e3a11ec5aaec3d2de37c6d1d23336a39552`  
**CI audited:** `34386858855`  
**Stage status:** `R-HIST-03D: IN PROGRESS — DEBUGGING`  
**R-HIST-03E:** GATED  
**R-HIST-03F:** GATED  
**Live-data verified:** NO  
**Production accepted:** NO  
**Model/strategy/execution authority changed:** NO  

---

## 1. Executive finding

The 03D failure is not one bug. It is two independent architectural defects plus one verification weakness.

```text
DEFECT A — deterministic semantic hashing
raw input
  -> model_construct()
  -> hash
  -> real Pydantic validation later changes the representation
  -> validator recomputes a different hash
  -> DATASET_MEMBER_HASH_MISMATCH

DEFECT B — typed retention
DATASET/MODEL/PROFILE/AUDIT semantic hash
  -> content_hash
  -> HistoricalRetentionAuthority
  -> lookup in market_data_objects
  -> semantically wrong namespace

WEAKNESS C — stored artifact verification
payload byte checksum + declared/indexed hash are checked,
but semantic Pydantic reconstruction/recomputation is not yet mandatory on the trusted read path.
```

The safe repair must solve all three without changing existing 03A/03B/03C market-evidence identities.

---

## 2. CI evidence

At exact head `47828e3a11ec5aaec3d2de37c6d1d23336a39552`, CI run `34386858855` completed with failure.

Observed backend split from the audit:

```text
1636 PASSED
16 FAILED

14 failures -> deterministic member/hash canonicalization collapse
 2 failures -> typed semantic-artifact retention defect
```

The Mypy job also failed. Most diagnostics are known legacy baseline errors. The 03D change introduced a clear new diagnostic around the dynamic `model_construct()` call in `selection/r18_history.py`; the normalized Mypy delta must be checked after the fix rather than treating all legacy diagnostics as a 03D regression.

---

## 3. Root cause A — builder and validator do not hash the same semantic object

The previous fix correctly changed Pydantic exclusion semantics from aliases to field names, e.g.:

```python
exclude={"member_id", "member_hash"}
```

However, the new helper still constructs canonical material with:

```python
draft = model_type.model_construct(
    **draft_values,
    **{computed_field: "0" * 64},
)
```

`model_construct()` bypasses Pydantic validation. That means nested objects, defaults, aliases and coercions may not be normalized before the builder computes the hash.

Example from the current dataset-member contract:

```python
evidence_roots: tuple[FrozenEvidenceRootV1, ...]
```

The test supplies dictionary input such as:

```python
{
    "role": "DECISION_MARKET_EVIDENCE",
    "contentHash": H5,
}
```

Before validation the builder can hash the raw dictionary form. After full Pydantic validation the same logical root becomes a `FrozenEvidenceRootV1` with normalized field representation and materialized defaults such as `runId=None` and `tradingDate=None`.

Therefore:

```text
SHA256(builder raw/unvalidated representation)
!=
SHA256(validator normalized representation)
```

This creates `DATASET_MEMBER_HASH_MISMATCH` and causes many apparently unrelated 03D tests to fail downstream.

### Non-negotiable hashing law

```text
RAW INPUT
    -> FULL PYDANTIC VALIDATION/NORMALIZATION
    -> CANONICAL SEMANTIC MATERIAL
    -> SHA-256
    -> IMMUTABLE PUBLIC OBJECT
    -> VALIDATOR RECOMPUTES FROM THE SAME MATERIAL CONTRACT
    -> SAME SHA-256
```

Do not hash raw input and then allow Pydantic to change its semantic representation afterward.

---

## 4. Required repair for deterministic semantic hashing

Remove `_normalized_material()` as an identity source if it depends on `model_construct()`.

Introduce internal material contracts that contain every semantic field but exclude only the self-referential identity field.

Required pattern:

```text
_FrozenDatasetMemberMaterialV1
    -> FrozenDatasetMemberV1 + member_id/member_hash

_FrozenDatasetManifestMaterialV1
    -> FrozenDatasetManifestV1 + dataset_hash

_GovernedModelVersionMaterialV1
    -> GovernedModelVersionV1 + model_hash

_StrategyProfileVersionMaterialV1
    -> StrategyProfileVersionV1 + content_hash

_GovernanceAuditRecordMaterialV1
    -> GovernanceAuditRecordV1 + record_hash
```

Builder rule:

1. remove any caller-supplied computed identity field;
2. run `MaterialModel.model_validate(values)`;
3. canonical-hash that validated material model;
4. create the public immutable object using the normalized material plus computed identity.

Validator rule:

1. reconstruct the same material contract from the public object excluding only its computed identity fields;
2. recompute canonical hash;
3. reject any mismatch.

This removes builder/validator canonicalization drift by construction.

### Mandatory deterministic-hash tests

- raw nested dict vs already-instantiated nested Pydantic model -> same hash;
- snake_case vs accepted alias form -> same hash;
- semantically equivalent tuple/list input after validation -> same hash where allowed by contract;
- equivalent timezone representations -> same normalized hash if the contract normalizes them;
- serialize -> reload -> validate -> same identity;
- mutate declared member/dataset/model/profile/audit hash only -> FAIL;
- mutate one semantic field -> recomputed hash changes or validation fails;
- change one evidence root -> FAIL;
- change one dataset member -> dataset identity changes/fails old hash.

---

## 5. Root cause B — semantic artifact hash is incorrectly typed as market `content_hash`

The current retention contract fundamentally treats `content_hash` as a market-evidence locator.

`HistoricalRetentionAuthority` explicitly resolves it from:

```text
market_data_objects.content_hash
```

That is correct for retained market objects.

It is incorrect for 03D semantic artifacts.

The current R18 staging path conceptually does:

```text
DATASET semantic hash
MODEL semantic hash
PROFILE semantic hash
AUDIT semantic hash
        -> content_hash
        -> HistoricalRetentionAuthority
        -> market_data_objects
```

This violates the required namespace separation:

```text
MARKET_OBJECT hash
!= DATASET hash
!= MODEL hash
!= PROFILE hash
!= AUDIT hash
```

The fact that every value is a 64-character SHA-256 digest does not make the identities interchangeable.

---

## 6. Required typed-retention contract

Do not rename or repurpose existing market `content_hash` because 03A/03B/03C already depend on its identity semantics.

Add a separate semantic-artifact locator:

```text
RetentionReference
- reference_id
- reference_type

# existing market evidence locator
- content_hash | null
- run_id | null
- trading_date | null

# new typed semantic artifact locator
- artifact_id | null
- artifact_version | null
- artifact_hash | null

- permanent
- retain_until
- created_at
```

For a semantic artifact, require the exact typed tuple:

```text
reference_type
+ artifact_id
+ artifact_version
+ artifact_hash
```

Do not use an ambiguous hash-only lookup.

Recommended fail-closed rule: a reference should not simultaneously use both `content_hash` and `artifact_hash` unless an explicit future contract defines why both namespaces are required.

---

## 7. Exact typed artifact resolution

The authority should resolve semantic references by type:

| Retention reference | Authoritative table | ID | Version | Semantic hash |
| --- | --- | --- | --- | --- |
| `ML_DATASET` | `ml_frozen_datasets` | `dataset_id` | `dataset_version` | `dataset_hash` |
| `MODEL_VERSION` | `ml_governed_model_versions` | `model_id` | `model_version` | `model_hash` |
| `STRATEGY_PROFILE` | `strategy_profile_versions` | `profile_id` | `profile_version` | current profile semantic hash column |
| `AUDIT` | `governance_audit_records` | `audit_id` | explicit/frozen audit version contract | `record_hash` |

Market evidence continues to resolve through the existing market tables.

```text
MARKET EVIDENCE
    content_hash/run_id/trading_date
        -> market_data_objects / market_data_manifests

SEMANTIC ARTIFACT
    type + id + version + artifact_hash
        -> exact 03D artifact table
```

No semantic artifact hash should be searched for in `market_data_objects`.

---

## 8. Outbox/database migration must be additive and legacy-safe

The producer outbox currently has no dedicated `artifact_hash` column.

Additive migration should add semantic-artifact columns without recreating the table or rewriting existing rows.

At minimum:

```sql
ALTER TABLE historical_retention_outbox
ADD COLUMN artifact_hash TEXT;
```

The retained-reference table should also gain the typed semantic-artifact locator required by the authority, including artifact ID/version/hash as needed by the final contract.

### Forbidden migration behavior

Do not:

- copy every existing `content_hash` into `artifact_hash`;
- reinterpret legacy market hashes as artifact hashes;
- manufacture historical artifact identity from current data;
- rewrite old outbox rows merely to fit the new schema;
- change historical event IDs/reference IDs.

---

## 9. Critical backward-compatibility rule — legacy event identity must not change

Existing 03A/03B/03C event identity is deterministic from the existing canonical payload/lineage fields.

If the new field is serialized as:

```json
"artifactHash": null
```

for every legacy event, old canonical bytes change and therefore old `lineage_digest`, `event_id`, and `reference_id` may change.

For legacy market events where `artifact_hash is None`, `artifactHash` must remain **absent**, not merely null.

Required behavior:

```python
payload = existing_legacy_payload_fields()
if self.artifact_hash is not None:
    payload["artifactHash"] = self.artifact_hash
```

Mandatory regression test:

```text
same existing legacy market retention intent
before typed-retention patch
vs after typed-retention patch
=> identical event_id
=> identical reference_id
=> canonical payload contains no artifactHash key
```

---

## 10. R18 producer change

The R18 semantic-artifact staging path must stop doing:

```python
content_hash=artifact_hash
```

It should stage:

```text
content_hash = null
artifact_hash = exact dataset/model/profile/audit semantic hash
artifact_id = exact artifact ID
artifact_version = exact immutable version
```

This change is required for:

```text
ML_DATASET
MODEL_VERSION
STRATEGY_PROFILE
AUDIT
```

while existing market-evidence producers remain unchanged.

---

## 11. Weakness C — trusted stored-artifact verification should recompute semantics

The stored 03D verifier currently checks serialized payload integrity and declared/indexed hash agreement. That is necessary but not sufficient as the final trusted verification boundary.

After byte-integrity and indexed-hash checks, it should reconstruct the exact typed Pydantic contract:

```text
ML_DATASET -> FrozenDatasetManifestV1
MODEL_VERSION -> GovernedModelVersionV1
STRATEGY_PROFILE -> StrategyProfileVersionV1
AUDIT -> GovernanceAuditRecordV1
```

The model validators must then recompute the semantic identity from normalized material.

Required trusted read chain:

```text
stored payload bytes
   -> payload checksum verification
   -> JSON parse
   -> exact artifact type selection
   -> Pydantic semantic validation
   -> semantic hash recomputation
   -> indexed type/id/version/hash verification
   -> trusted artifact
```

Also ensure AUDIT is covered by the typed verifier rather than remaining outside the same verification contract.

---

## 12. Hash responsibilities must remain distinct

Immediate safe terminology/semantics:

```text
content_hash
= market-object semantic/content locator used by historical market evidence

artifact_hash
= dataset/model/profile/audit semantic identity used by typed artifact retention

stored payload/content checksum
= SHA-256 over exact serialized artifact payload bytes

outbox.payload_hash
= integrity hash over the retention-intent envelope
```

Do not collapse these simply because all use SHA-256.

A later generalized EvidenceReference may expose semantic/payload/lineage hashes explicitly, but 03D should make only the minimum safe additive change needed to type these identities correctly.

---

## 13. Mandatory acceptance matrix before 03D PASS

The repair should survive at least the following:

1. same logical member from raw dict/nested-model inputs -> same `member_hash`;
2. aliases/default normalization cannot change identity after builder hashing;
3. serialize/reload/revalidate -> same hash;
4. alter declared member hash -> FAIL;
5. alter one member semantic field -> FAIL;
6. alter one evidence root -> FAIL;
7. alter dataset member -> FAIL;
8. alter dataset payload while keeping declared dataset hash -> FAIL;
9. alter model semantics while retaining model hash -> FAIL;
10. alter profile rules while retaining profile hash -> FAIL;
11. alter audit content while retaining record hash -> FAIL;
12. unknown `artifact_hash` -> FAIL;
13. semantic artifact hash is never resolved through `market_data_objects`;
14. legacy market `content_hash` still resolves through current market authority;
15. legacy event IDs/reference IDs are unchanged;
16. old outbox rows without `artifact_hash` still dispatch correctly;
17. additive migration does not rewrite old rows;
18. tampered artifact before dispatch -> `FAILED_BLOCKING`;
19. failed semantic-artifact registration creates no retention reference;
20. artifact + outbox stay in one producer transaction;
21. injected failure/rollback leaves neither artifact nor outbox;
22. typed semantic artifact hash does not pollute market `content_hashes` protection semantics;
23. disappearance/tampering of a permanently retained typed artifact fails closed;
24. full 03A/03B/03C regression suite remains green;
25. full backend suite passes;
26. Ruff passes;
27. compile verification passes;
28. normalized Mypy diagnostic delta introduces no new 03D errors.

---

## 14. Golden historical graph required before higher-level intelligence

Canonical attack scenario:

```text
10:25:00 INFY candle closes
10:25:02 candle becomes known
10:26:00 source snapshot S1 becomes known
10:27:00 opportunity O1 created: INFY / 5m / continuation / LONG
10:27:xx profile P4 evaluates O1
10:27:xx model M12 scores O1
10:28:00 decision D1 = WATCH
10:31:00 corrected source S2 arrives
```

Replay at `10:28` must use S1 and categorically reject S2 even if S2 carries an older market/event timestamp.

Attack the graph:

```text
replace S1 -> FAIL
delete S1 -> FAIL
replace old decision with newer/latest decision -> FAIL
change P4 -> FAIL
change M12 -> FAIL
change feature definition -> FAIL
change label policy -> FAIL
alter opportunity direction -> FAIL
alter dataset member -> FAIL
alter one payload byte -> FAIL
```

Exact historical graph replay must produce the same hashes, same opportunity, same model/profile binding, and same WATCH decision.

This golden graph belongs centrally in 03F acceptance, but 03D must establish the typed immutable identities that make that test possible.

---

## 15. Safe implementation order

```text
STEP 1
Replace pre-validation/model_construct hashing with validated material contracts.
Make member/dataset/model/profile/audit builders and validators consume the same canonical material.

STEP 2
Add typed semantic-artifact retention fields additively.
Preserve existing market content_hash behavior.

STEP 3
Change R18 semantic artifact staging from content_hash=artifact_hash to the typed artifact locator.

STEP 4
Teach HistoricalRetentionAuthority exact typed semantic-artifact resolution.

STEP 5
Strengthen stored artifact verification with exact Pydantic semantic recomputation.

STEP 6
Run focused 03D adversarial tests.

STEP 7
Run all 03A/03B/03C regression tests.

STEP 8
Run full backend suite, Ruff, compile verification and normalized Mypy delta.

STEP 9
Only if all gates pass: mark R-HIST-03D PASS.

STEP 10
Only then start R-HIST-03E.
```

---

## 16. Scope/safety constraints

This repair must **not**:

- change model promotion authority;
- activate a strategy/profile;
- change live-order or broker execution behavior;
- merge the PR automatically;
- skip 03D acceptance because a subset of tests turns green;
- backfill missing history with present-day values;
- replace exact historical versions with latest/current versions.

This is a historical memory / reproducibility / governance repair only.

---

## 17. Recorded status

```text
R-HIST-03A: PRESERVE
R-HIST-03B: PRESERVE
R-HIST-03C: PRESERVE

R-HIST-03D: IN PROGRESS — TWO ROOT DEFECTS + VERIFICATION WEAKNESS RECORDED
R-HIST-03E: GATED
R-HIST-03F: GATED

AUDITED HEAD BEFORE NOTE:
47828e3a11ec5aaec3d2de37c6d1d23336a39552

AUDITED CI:
34386858855 — FAILED

LIVE-DATA-VERIFIED: NO
PRODUCTION-ACCEPTED: NO

MODEL AUTHORITY CHANGED: NO
STRATEGY AUTHORITY CHANGED: NO
EXECUTION AUTHORITY CHANGED: NO

PR #6 MERGED: NO
```

This note is intentionally documentation-only. It records the root cause and repair contract so a later implementation cannot accidentally "fix the tests" while preserving the underlying semantic-identity defect.