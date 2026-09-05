# Dependency And License Review

This review records licenses shipped in the installed Python distributions on 2026-07-11. It is an engineering inventory, not legal advice.

## Core Runtime

| Package | Verified version | Packaged license | TrendForge use |
| --- | ---: | --- | --- |
| FastAPI | 0.135.1 | MIT | API framework |
| Uvicorn | 0.42.0 | BSD-3-Clause | Local ASGI server |
| Pydantic | 2.12.5 | MIT | Typed contracts |
| yfinance | 0.2.58 | Apache-2.0 | Unofficial temporary research adapter only |
| pandas | 2.3.3 | BSD-3-Clause | Dataframes and import normalization |
| NumPy | 2.4.3 | BSD-3-Clause plus bundled notices | Numerical calculations |
| PyArrow | 23.0.1 | Apache-2.0 | Parquet storage |
| openpyxl | 3.1.5 | MIT | Official spreadsheet disclosure parsing |
| nselib | 2.5.1 | Apache-2.0 | Optional unofficial EOD wrapper |

The static frontend has no runtime npm dependencies.

## Excluded By Default

| Package | Installed version reviewed | Finding | Enforcement |
| --- | ---: | --- | --- |
| pyharmonics | 1.5.3 | Metadata classifier says MIT, but the packaged `LICENSE` is an NOC license that says use is forbidden. | Removed from core requirements. Adapter does not import unless `TRENDFORGE_ENABLE_PYHARMONICS=1` is explicitly set after separate review. Internal validator is authoritative. |
| nsepython | 2.97 | Packaged license is GPL-3.0. | Removed from core requirements. Adapter fails closed unless `TRENDFORGE_ENABLE_GPL_NSEPYTHON=1` is explicitly set after separate review. Official archive adapters are preferred. |
| stock-pattern | not installed | Upstream is GPL-3.0. | Reference only; no copied source. |

No code from TradingView scripts, commercial scanners, `stock-pattern`, `pyharmonics`, or `nsepython` is copied into the TrendForge core.

## Verification

Inspect installed metadata and packaged license files before changing versions. A package classifier alone is insufficient when the distributed license file conflicts with it.

```powershell
cd backend
python -m pip check
python -m pip show fastapi uvicorn pydantic yfinance pandas numpy pyarrow openpyxl nselib
```

## 2026-07-17 Source Merge Dependency Decision

The twelve-route merge introduced no runtime package or license change. It
uses the existing HTTP/session, JSON/HTML parsing and SQLite/archive paths.
No NSE wrapper, browser automation package, CFTC client package or copied
open-source downloader was added. This preserves the existing dependency and
license review boundary.

## 2026-07-20 Indicator Engine Pin Decision

DAT-011 introduced no new package. The registered engine identity is
`trendforge.numpy-pandas` `1.0.0`, using the already installed NumPy `2.4.3`
and pandas `2.3.3`. TA-Lib, pandas-ta and other indicator wrappers were not
added. A future NumPy/pandas or engine upgrade must change the registered pin
and pass reviewed parity fixtures before activation.

The focused mypy run that followed imports reported missing pandas stubs plus
existing typing defects in imported modules. `pandas-stubs` was not installed;
installing it or any other dependency requires separate approval. Runtime and
Ruff verification are recorded in `VALIDATION.md`, without a false clean-mypy
claim.

