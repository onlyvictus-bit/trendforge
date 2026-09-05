# MD69-M5 Work Packet — Timestamp Alignment and Panel Bridge

Status: **COMPLETE — VERIFIED at the temporary canonical-manifest ceiling**

## Intent and ceiling

INTENT: record source hashes/timestamps for derived inputs, reject incompatible
spot/futures/options bundles, and make live panels consume a cloned read-only
projection of the canonical MD69 manifest when the MD69 collector is enabled.

The catalog JSON remains immutable. Consensus formulas and screener scoring are
not changed. No production migration or collector activation is in scope.

## Done criteria

1. Derived bundles contain source key, object hash, data timestamp, fetch
   timestamp and maximum skew.
2. Missing, wrong-day, future, or over-skew inputs return `WAIT`, never a value.
3. Canonical provider validates manifest/object paths and current-date/freshness.
4. Canonical panel mode never constructs the legacy NSE fetch client.
5. Panel overlay is rebuilt from cloned records; catalog objects are unchanged.
6. Consensus protected hash and screener financial golden outputs remain stable.

## Observed result

- Derived bundles fail closed on missing, wrong-day, future, or over-skew input.
- The canonical provider reads SQLite in read-only mode, verifies the manifest
  file hash and every referenced object hash, and clones normalized records.
- Canonical mode never constructs the legacy NSE client and never falls back to
  static catalog prices after a provider failure.
- `main.py` selects the canonical provider only when
  `MARKET_DATA_69_ENABLED=1`; the production flag remains off.

```text
alignment + existing live-panel tests: 17 passed
combined MD69 M1-M5 backend tests: 87 passed, 1 warning
all frontend Node suites: 10 passed
Ruff: All checks passed
Python compilation: PASS
consensus.js SHA-256: FADD34BA723AA72562D18ACF77629E01415834FCC6F2A24DA594FD2672BABDA4
screener.js SHA-256: DA72C82800E8E465D4130DA180265B581650AE4DBB04CE604D12DEE10A989F2A
links_105.json SHA-256: 668C0E026E43012C91B8B6176B1D642091C805E34CB779343D2274D447283025
```

No production migration, market fetch, scheduler process, consensus voter,
screener formula, broker path, quantity path, or order path was activated.
