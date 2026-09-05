# Dead Source Route Quarantine — 2026-08-11

## Approved outcome

Keep verified dead/unusable routes as visible historical hints, while making
them impossible to fetch, schedule, normalize, score, or publish as active
catalog links. Working replacement contracts remain unchanged.

## Quarantined routes

| Historical route | Status | Active replacement |
|---|---|---|
| Yahoo `^BADI` | `NOT_IN_USE` — zero price rows | `tradingeconomics_bdi`; `yahoo_bdry_shipping_proxy` is proxy-only |
| `pytrends` | `NOT_IN_USE` — unofficial/archived/rate-limited | `google_trends_india_rss` for current topics only |
| StockEdge "API" | `NOT_IN_USE` — no verified public API contract | official NSE/BSE/NSDL source families |
| BSE `FIIDII/w` | `NOT_IN_USE` — HTML shell | `bse_fii_dii` via `CategoryTurnover/w` |
| BSE `ParticipantWiseOI/w` | `NOT_IN_USE` — HTML shell | `bse_participant_oi` via `DeriMarketDisclosureData_ng/w` |

Machine-readable authority:
`D:\TrendForge\config\source_route_quarantine.yaml`.

## Flow

```text
historical dead URL -> quarantine hint -> no acquisition role
working replacement -> typed registry -> resolver/parser -> last-good store
                    -> informational catalog/panels under existing role rules
```

The incoming Pack-1 prototype retains two compatibility function names, but
their bodies are no-network/no-write stubs and its main routine does not call
them. StockEdge inventory URLs compile as `NOT_IN_USE` and cannot unlock any
research state. MCX is not quarantined because it is intermittent and retains
its last populated dataset.

## Verification

- `test_dead_source_route_quarantine.py`: 4 passed.
- `test_market_data_registry.py`: 13 passed.
- saved-link classification API check: 1 passed.
- Python compile: changed Python files compiled successfully using an isolated
  bytecode directory.
- Registry remained 119 rows / 119 unique keys.
- Catalog remained 161 rows / 125 active logical keys.
- No consensus or screener formula file changed.
