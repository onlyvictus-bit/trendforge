# 30 Screener Sources — COMPLETE

**Status: FINISHED** (collector registry expanded **69 → 99**)  
**Date:** 2026-08-06  
**Source file:** `C:\Users\sakth\Downloads\30 LINK FOR SCRENER.txt`

**Next pack (planned, not pinned):** 40+ institutional / macro / vendor links —  
see [`ADD_40_SCREENER_LINKS_PLAN.md`](./ADD_40_SCREENER_LINKS_PLAN.md).

## Final registry size

| Milestone | Count |
|-----------|------:|
| Original MD69 | 69 |
| Phase-1 | 76 |
| Phase-2 | 83 |
| Phase-3 multi-step | 87 |
| **Finish set** | **99** |

Filename remains `config/source_refresh_registry_69.csv` (path compatibility).  
`EXPECTED_SOURCE_COUNT = 99` with SHA pins updated.

## All finish-set sources (added last)

- `yahoo_cme_proxy`, `yahoo_lme_proxy`
- `mcx_market_watch`, `mcx_option_chain`, `mcx_top_participants`
- `mcx_warehouse_stocks`, `mcx_delivery_reports`
- `ncdex_bhavcopy`
- `amfi_portfolio_disclosure`
- `nse_bulk_deals_today_csv`, `nse_bulk_deal_symbol`
- `nse_quote_equity_trade_info`

Plus Phase-1/2/3: ban, MTO, short, preopen cash, BSE FO bhav, AMFI NAV, participant OI, insider, index OC, LBMA, EIA natgas, WASDE, FII FO stats, RBI USDINR POST, OC v3, CDSL, DGCIS, etc.

## Front-end feed cards (catalog merge + sample fill)

The bar **“Showing N feeds on page (painted …)”** counts **catalog primaries**
after mirror collapse — not the registry number alone.

| Layer | File | Role |
|-------|------|------|
| Collector jobs | `source_refresh_registry_69.csv` (99 keys) | Download / save |
| Catalog cards | `links_105.json` | Paint feeds, minimize, Details |
| Merge script | `merge_registry_into_catalog.py` | Add missing registry keys as cards |
| Sample fill | **`fill_catalog_samples_from_collector.py`** | Last-good → `records_sample` (Path A) |
| Count bar | `app.js` `applyFiltersAndRender` | N = `displayList.length` |
| Test | `tests/catalog_registry_merge.test.js` | Fail if registry key has no card |

**Verified (2026-08-06):** inventory **141** · ~**98** primaries · **99** registry
keys · **29** new cards sample-filled from collector → STRONG tables.

### Path A vs Path B (do not confuse)

| Path | Surface | Who writes samples |
|------|---------|-------------------|
| A | Catalog cards / drawer | `fill_catalog_samples_from_collector.py` (or legacy `generate_json.py`) |
| B | Sector / Consensus / Screener | Live `inventoryOverlay` only — **not** catalog JSON |

## How to add another link later (same process)

Full checklist: inventory `ARCHITECTURE.md` **§15** and
`MD69_REFRESH_OPERATION_REFERENCE.md` **§8**.

```text
# A) Collector
# wire parser + CSV + YAML + EXPECTED_SOURCE_COUNT pins
# restart API with MARKET_DATA_69_ENABLED=1
POST http://127.0.0.1:8000/api/market-data/refresh

# B) Catalog
cd D:\trendforge_inventory_app
python merge_registry_into_catalog.py
python fill_catalog_samples_from_collector.py
# browser Ctrl+Shift+R → http://127.0.0.1:8080/
```

## How to run (99-pin)

```text
MARKET_DATA_69_ENABLED=1
MARKET_DATA_69_PROVISIONAL_OVERRIDE=1
# one uvicorn on 127.0.0.1:8000
POST /api/market-data/refresh
GET  /api/panels/live
# catalog fill scripts above if cards empty
```

## Notes

- MCX/NCDEX may use Yahoo research proxies when exchange WAF blocks the IP.
- Trade-info / bulk-by-symbol use RELIANCE sample scope (fan-out later if needed).
- Consensus / A-only screener score policy unchanged.
- If Refresh fails: API down or `LEASE_HELD` (clear `market_data_scheduler_leases`).
