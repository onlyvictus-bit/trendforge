# MD69-M3 Work Packet — Unified Acquisition and Normalization

Status: **COMPLETE — VERIFIED**

## Intent and ceiling

INTENT: orchestrate the existing `AsyncEndpointClient` and resolver paths
through one bounded service that emits one normalized result per source and can
commit validated results to the MD69 store. Reuse bytes only for
`RESPONSE_REUSE`; `SESSION_SHARING` means separate requests through one client.

No background scheduler, production DB, live activation, panel mutation,
consensus formula, screener score, broker, quantity, or order path is in scope.

## Allowed surfaces

- `backend/trendforge_api/market_data_service.py`
- `backend/tests/test_market_data_service.py`
- MD69 status, architecture, traceability, review, and validation docs

Pre-edit runtime manifest hash:
`1A4EAA1ADB95260241892105481FBC4D85B1824D01D7830AF6FC69A965F574BE`

## Done criteria

1. All 69 compiled contracts have a supported structured or named normalizer.
2. Required parameter/fan-out providers fail closed when inputs are absent.
3. Global/domain concurrency caps and per-domain circuit breaking are observed.
4. Response reuse downloads once; session-sharing sources remain separate.
5. Empty semantics and parser failures cannot replace last-good state.
6. One failing source cannot cancel unrelated sources.
7. Tests use injected offline transports; no live market call is made.

## Observed result

- 19/19 service tests passed; the combined registry/store/service/parser suite
  passed 82/82 with one dependency deprecation warning.
- All 69 contracts resolve to a supported structured or named normalizer.
- Physical response reuse, session-only sharing, parameter fan-out,
  global/domain caps, queued circuit breaking, valid-empty semantics,
  failure isolation, future-date quarantine, and last-good preservation were
  observed using injected offline transports.
- Ruff and Python compilation passed. No live call or production write ran.
