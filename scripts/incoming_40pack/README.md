# Incoming script pack — audit only (NOT wired into MD69)

**Source:** `C:\Users\sakth\Downloads\1.txt` (joined marketing + 3 scripts)  
**Staged:** 2026-08-10  
**Status:** Audit / split complete. **Do not run as a second TrendForge pipeline.**

## Files here

| File | Role |
|------|------|
| `1_joined_audit_LATEST.txt` | Unchanged original (also timestamped copy) |
| `market_data_downloader.py` | Standalone downloader |
| `market_data_parser.py` | Standalone parser → Parquet |
| `market_data_pipeline.py` | Orchestrator: download then parse |
| `fii_sources.py` | Standalone third-party FII **holding-% change** fetch (audit only). Official Refresh path is MD69 pin 123 (`screener_in_fii_holding_change` etc.). Not daily FII tape. Do not run this as a second pipeline. |

## Standalone behaviour (problems for MD69)

- Writes local `./market_data/` tree + Parquet under `processed/`
- Mon–Fri “trading days” only (no TrendForge calendar)
- HTTP status checks; no `source_key` / content hash / last-good / manifest
- `CFTC_YEAR = 2026` hard-coded
- Needs `requests`, `pandas`, `openpyxl`, `pdfplumber`; Parquet needs `pyarrow` or `fastparquet` (not listed in script header for parser)

## Feed → existing MD69 `source_key` map

| Standalone feed | Action | Existing / planned key |
|-----------------|--------|-------------------------|
| CFTC COT reports | **MAP / enhance** | `cftc_cot`, `cftc_legacy_futures_only`, `cftc_disagg_futures_only`, `cftc_tff_futures_only` |
| NSE FII/DII cash | **MAP / enhance** | `nse_fii_dii` |
| NSE participant OI | **MAP / enhance** | `nse_participant_oi` |
| NSE FII derivatives | **MAP / enhance** | `nse_fii_derivatives_stats` |
| BSE participant OI | **PINNED** (live path ≠ pack URL) | `bse_participant_oi` → `DeriMarketDisclosureData_ng/w` (pack `ParticipantWiseOI/w` dead) |
| BSE FII/DII | **PINNED** (live path ≠ pack URL) | `bse_fii_dii` → `CategoryTurnover/w` (pack `FIIDII/w` dead) |
| MSE participant OI | **NOT pinned** | `www.msei.in` connect timeout here; no live XLSX verify |
| MCX warehouse PDFs | **MAP / enhance** | `mcx_warehouse_stocks`, `mcx_delivery_reports` (+ ComRIS plan keys) |

## Dead-route quarantine

The following historical ideas are **NOT_IN_USE** and remain only as migration
hints: Yahoo `^BADI`, `pytrends`, StockEdge "API", BSE `FIIDII/w`, and BSE
`ParticipantWiseOI/w`. Their reasons and approved replacements are recorded in
`D:\TrendForge\config\source_route_quarantine.yaml`.

The two BSE compatibility functions in `market_data_downloader.py` are
non-network stubs, and the script main path no longer calls them. Do not replace
their stubs with HTTP requests. MCX is not quarantined: its WAF failures are
intermittent and the production collector preserves the last good dataset.

**Rule:** Reuse URL/cookie/PDF parse **logic** inside TrendForge resolver/parsers.  
Do **not** register parallel keys that only re-download the same NSE/BSE files into Parquet.

## Integration order (recommended)

1. Steal cookie/header patterns for NSE/BSE that already fail with 403 on some IPs.  
2. Improve `nse_fii_dii` / `nse_participant_oi` / `nse_fii_derivatives_stats` using downloader code.  
3. MCX PDF table extraction → improve warehouse keys if WAF allows.  
4. CFTC: align year/dynamic ZIP with existing CFTC parsers.  
5. Only then add **new** BSE/MSE keys via ADD_40 + registry pin bump.

## Optional offline smoke (not MD69)

```bash
cd D:\TrendForge\scripts\incoming_40pack
pip install requests pandas openpyxl pdfplumber pyarrow
python market_data_pipeline.py
# writes ./market_data/ under this folder cwd
```

Still **not** a substitute for `POST /api/market-data/refresh`.
