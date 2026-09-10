# R-HIST-03D PR #6 Failure Repair and Validation Record — 2026-09-10

## Scope

This record captures the observed PR #6 exact-head CI failure, root causes, locally reproduced repair, GitHub implementation changes, validation law, and remaining 03D production gates.

Repository: `onlyvictus-bit/trendforge`

PR: `#6` — `R-HIST-03: exact S8 lineage, retained outcomes and immutable revisions`

Pre-repair exact head inspected: `46ab301d2a8f8a09a98b79f1f0577075b5213564`

Pre-repair exact-head CI: run `34452754078` / workflow `ci` / run #76 / `FAILURE`.

03C accepted baseline remains `2079336768907cf9f0668a8798cd631007c6e74f`, CI `34355244517`: 1,623 backend tests passed, Ruff passed, frontend passed, and the normalized Mypy delta versus its legacy baseline was zero. The legacy Mypy baseline itself was not clean and must not be described as a Mypy pass.

No model authority, strategy authority, automatic promotion authority, broker authority, or execution authority is granted by this repair.

## Pre-repair exact-head failure summary

Observed exact-head run `34452754078`:

- backend: `21 failed, 1641 passed, 2 warnings`
- frontend: success
- typecheck: failed with `513 errors in 71 files (checked 274 source files)`
- known 03C baseline: `512 errors in 70 files`
- new 03D diagnostic: `trendforge_api/selection/r18_history.py:84: Need type annotation for "adapter" [var-annotated]`
- Ruff did not execute because backend tests failed before the Ruff step.

The 21 backend failures separated into three root-cause groups.

## Root cause 1 — builder/verifier semantic hash mismatch

`_normalized_material()` validated each field with `TypeAdapter`, then serialized it using:

```python
adapter.dump_python(validated, mode="json")
```

The public identity validators later recomputed the semantic material using:

```python
self.model_dump(mode="json", by_alias=True, ...)
```

For nested `FrozenEvidenceRootV1` values, the builder material therefore used Python field names:

- `content_hash`
- `run_id`
- `trading_date`

while the public verifier used the canonical aliased names:

- `contentHash`
- `runId`
- `tradingDate`

That means the builder and verifier hashed different JSON bytes for the same logical object.

The exact locally reproduced fixture produced:

- pre-repair builder hash: `2eb3a7e8384156e7358231727cce013c9bc7502f6444b79d40b81e1f573d6874`
- verifier hash: `dd7e7a3c44cd27238de5221ddaba6571233207e3cf630cb766af85cde84ac4e9`

This caused the `DATASET_MEMBER_HASH_MISMATCH` failure and cascaded through dataset, model, profile, persistence and governed-read tests.

### Repair

`backend/trendforge_api/selection/r18_history.py`

The TypeAdapter instance is explicitly typed and JSON serialization now uses aliases:

```python
adapter: TypeAdapter[Any] = TypeAdapter(field.annotation)
validated = adapter.validate_python(raw)
material[alias] = adapter.dump_python(validated, mode="json", by_alias=True)
```

This makes the temporary field-validation builder path serialize nested objects consistently with the public `model_dump(..., by_alias=True)` verifier and removes the new 03D `var-annotated` Mypy diagnostic.

This is a narrow CI repair. The broader 03D identity-contract hardening remains a production gate: semantic JSON still requires a single explicitly governed value domain, strict rejection of non-finite floats/arbitrary objects, removal of `default=str` from the semantic identity path, explicit hash-case normalization rules, UTC identity normalization, and explicit collection-order semantics.

## Root cause 2 — retention validator inferred identity domain from reference type

03D introduced typed semantic retention for:

- `ML_DATASET`
- `MODEL_VERSION`
- `STRATEGY_PROFILE`
- `AUDIT`

But legacy retention already used some of the same reference types (`ML_DATASET` and `AUDIT`) for market-evidence retention with locators such as `content_hash`, `run_id`, or `trading_date`.

The pre-repair validator rejected any typed-capable reference type that did not carry artifact identity:

```python
elif self.reference_type in TYPED_ARTIFACT_REFERENCE_TYPES:
    raise ValueError("typed 03D retention reference requires artifact identity")
```

That broke valid legacy market-evidence references merely because their enum type was also used by 03D.

### Correct identity law

Identity domain is determined by the locator fields supplied, not by the enum name alone:

```text
market locator present, no artifact locator
    -> legacy market-evidence mode

artifact locator present, no market locator
    -> typed 03D semantic-artifact mode

both or neither
    -> fail closed
```

Typed artifact mode still requires the complete tuple:

```text
artifact_id + artifact_version + artifact_hash
```

and typed artifact identity is only permitted for the defined 03D artifact reference types.

### Repair

`backend/trendforge_api/historical_retention.py`

The broad `reference_type`-only rejection was removed. Existing fail-closed rules remain:

- mixed market + artifact identities are rejected;
- partial artifact identities are rejected;
- artifact identity attached to a non-03D market reference type is rejected;
- permanent/temporary retention rules remain unchanged;
- legacy market evidence continues through the existing market object/manifest verification path;
- typed artifacts continue through exact artifact identity and semantic verification.

## Root cause 3 — invalid test fixture assumption

`test_profile_retention_uses_artifact_hash_not_fake_market_object` correctly proved that a strategy-profile semantic hash is placed in `artifact_hash`, not `content_hash`.

The test then queried:

```sql
SELECT COUNT(*) FROM market_data_objects WHERE content_hash=?
```

but that research-DB fixture did not create the `market_data_objects` table. The failure was:

```text
sqlite3.OperationalError: no such table: market_data_objects
```

Creating a fake market table/object merely to satisfy this assertion would weaken the namespace-separation test.

### Repair

`backend/tests/test_rhist03d_artifact_retention.py`

The test now proves the actual invariant directly in the two retention namespaces available in the fixture:

- the semantic profile hash never appears as `historical_retention_outbox.content_hash`;
- the semantic profile hash never appears as `historical_retention_references.content_hash`;
- the same value remains correctly represented as `artifact_hash`.

This tests the intended contract without inventing market evidence.

## Local pre-GitHub verification

Before applying the repair to PR #6, an isolated local harness reproduced the exact nested-alias mismatch and exercised the repaired semantics.

Focused local result: `7 passed` plus Python compile validation.

Covered behaviors included:

1. exact nested-alias dataset-member hash reproduction and round-trip;
2. same-symbol independent opportunity identity;
3. dataset member-order-independent identity;
4. governed model semantic hash round-trip;
5. strategy-profile semantic hash round-trip;
6. governance-audit semantic hash round-trip;
7. legacy `ML_DATASET` content-hash retention;
8. legacy `AUDIT` run/date retention;
9. complete typed 03D identity acceptance;
10. partial typed identity rejection;
11. typed artifact identity on market-only reference types rejection;
12. mixed identity-domain rejection;
13. legacy temporary-retention error behavior;
14. schema-safe proof that semantic artifact hashes do not enter the market `content_hash` namespace.

Local focused tests are evidence for the repair mechanism; they are not the 03D acceptance gate. GitHub exact-head CI and the remaining 03D production-hardening matrix remain authoritative.

## GitHub repair commits

The repair was applied to the existing PR #6 branch `feat/rhist03-producer-wiring` without merging the PR:

1. `c044eb765bba2fb2f3bb847d6f4b73fdbc52b8f6`
   - test: replace nonexistent `market_data_objects` fixture assumption with direct namespace-separation assertions.
2. `99d64d5b39ffc40b0990d9cfeec1df41dc16631e`
   - runtime: serialize normalized semantic material with `by_alias=True` and explicitly type `TypeAdapter[Any]`.
3. `68704a1bd3a4569d1d68201c079241ea41d708eb`
   - runtime: preserve legacy market-evidence mode for typed-capable reference enum values; retain fail-closed typed identity validation.

This documentation commit is intentionally separate from the code/test changes so the observed failure, repair and acceptance reasoning are preserved for future implementation work.

## Exact-head CI acceptance law

Do not declare this repair or 03D green because focused tests passed.

For the newest PR #6 exact head, verify:

1. exact PR head SHA resolved from GitHub;
2. workflow run is associated with that head (or the normal PR merge checkout is proven tree-equivalent to it);
3. backend has zero test failures;
4. Ruff passes;
5. frontend passes;
6. Mypy is compared against the accepted 03C normalized baseline and introduces zero new diagnostics; do not require unrelated legacy Mypy debt to be cleaned as part of 03D;
7. no unexpected migration, historical-identity, PIT or authority regression appears.

If any check fails, stop 03D and investigate the new failure. Do not advance to 03E.

## Remaining 03D production gates after CI repair

A green CI after these fixes removes the current regression set; it does not by itself prove the full R-HIST-03D contract complete. The approved production-hardening work still requires at minimum:

- strict semantic value-domain canonicalization and removal of `default=str` from semantic identity;
- explicit lower-case hash normalization/identity law;
- explicit UTC/time and collection-order identity law;
- Phase-0 inventory for pre-fix 03D events/references, including a hard stop if any malformed pre-fix semantic event was truly APPLIED;
- no in-place rewrite of immutable old outbox/reference identity;
- controlled supersession/quarantine/rebuild rules for old PENDING/FAILED_BLOCKING 03D events;
- database immutability guards allowing only `PENDING_RETENTION -> APPLIED` while rejecting identity/payload updates and DELETE;
- finalizer crash-window and two-finalizer concurrency matrix;
- transient-vs-semantic retention dispatch error taxonomy so SQLite lock/busy conditions do not become irreversible semantic failures;
- upstream R16/S8 exact owner + PIT/known-at proof, including backdated-correction rejection;
- downstream exact training/evaluation/holdout/model/profile/audit parent proof;
- full 03A/03B/03C regression preservation;
- exact-head CI verification at the final 03D acceptance commit.

## Stage boundary

Current intended order remains:

```text
03A PASS
 -> 03B PASS
 -> 03C PASS
 -> 03D repair + hardening + acceptance
 -> only if 03D PASS: 03E
 -> only if 03E PASS: 03F
 -> only after 03A..03F pass together: FULL R-HIST-03
```

Do not implement 03E or 03F merely because the current regression set is repaired.

LIVE-DATA-VERIFIED: NO.

PRODUCTION-ACCEPTED: NO.

PIT/model/strategy/execution authority: unchanged.
