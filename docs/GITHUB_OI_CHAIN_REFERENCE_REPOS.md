# GitHub reference repos — Live OI + Option Chain (extra details)

**Date:** 2026-07-27  
**Status:** **REFERENCE / BUILD FALLBACK ONLY** — not File A authority, not product data spine  
**Use when:** build issues on OI dashboard, chain fetch/parse, UI layout, or PCR/max-pain display helpers  
**Do not use as:** gate source, CONFIRMED unlock, dual voter, or replacement for inventory keys  

---

## 0. How TrendForge is allowed to use these three

| Allowed | Not allowed |
|---------|-------------|
| Read code for **ideas** (fetch headers, chain walk, PCR table UI) | Import their runtime as authority for state |
| Port **pure helpers** into `options_intelligence/` after rewrite + tests | Ship their win-rate / SSI / 4-factor trade scores as product truth |
| Run offline/demo **side-by-side** for human research | Feed Shoonya/yfinance path into File A gates without separate validation |
| Steal **layout** for OI Analysis / Strike Explorer | Add orders, auto-trade, or qty from any of these |
| Pin commit + license review before any copy | Silent merge of bullish/bearish OI folklore into CONFIRMED |

```text
Build order (still):
  1) Official inventory: nse_fo_bhavcopy, nse_oi_spurts, nse_option_chain*, live_equity_derivatives*
  2) If stuck → open these 3 repos for patterns
  3) Re-implement inside TrendForge contracts (fail-closed, lineage, no silent fill)
  4) Never: their score owns WATCH/WAIT/CONFIRMED/REJECT
```

**Map to our tools**

| Our tool | Primary GitHub helper |
|----------|------------------------|
| Live OI Dashboard (OI Analysis / Tracker / Index FO) | `nse-oi-dashboard` (+ et-signal-radar UI ideas) |
| Option Chain Analyzer (Strike / Expiry) | `Python-NSE-Option-Chain-Analyzer` (+ nse-oi-dashboard IV/OI) |
| Radar / multi-factor shell | `et-signal-radar` (UI/API shell only; drop SSI as state) |

---

## 1. Repo index (saved links)

| # | Repo | URL | Role for us |
|---|------|-----|-------------|
| **G1** | **et-signal-radar** | https://github.com/krishnabhokare27/et-signal-radar | Multi-stock radar UI + FastAPI shell + FII/DII + sector pulse ideas |
| **G2** | **nse-oi-dashboard** | https://github.com/raghavs-stack/nse-oi-dashboard | Live NIFTY/BN OI dashboard, PCR, max pain, IV tabs, GUI/terminal |
| **G3** | **Python-NSE-Option-Chain-Analyzer** | https://github.com/VarunS2002/Python-NSE-Option-Chain-Analyzer | Classic NSE website chain fetch + refresh loop + OI boundary/PCR table |

---

## 2. G1 — et-signal-radar

**URL:** https://github.com/krishnabhokare27/et-signal-radar  
**What it is:** ET AI Hackathon–style NSE screening dashboard (agents, engine, static glass UI).  
**Stack (from README):** Python 3.12, FastAPI, uvicorn, `yfinance`, NSE public APIs, pandas/pandas-ta, vanilla HTML/CSS/JS.

### Useful if we hit build issues

| Area | Steal carefully |
|------|-----------------|
| FastAPI route layout | `/api/nifty/pulse`, stock scan endpoints → compare to our discovery API shape |
| Frontend shell | `static/dashboard.html` — headers, pulse, sector feel for radar |
| Data feed split | `data/feeds.py` patterns (not yfinance as authority) |
| FII/DII display | Regime strip ideas only (our rule: never stock sponsor) |

### Reject / quarantine from this repo

| Feature | Why |
|---------|-----|
| **Signal Strength Index (SSI) 0–100** | Proprietary confluence score — same class as Combined_Score; not product state |
| Directional AI buy/sell signals | Not research-only four-state law |
| Observation zones as “entry/target/stop” product truth | Can show as research levels only with disclaimer |
| `yfinance` as live NSE truth | Secondary; inventory official first |
| Win-rate backtest as UI truth | Evidence ≠ P(win) |

### Suggested clone path (optional, offline)

```text
D:\TrendForge\reference\github\et-signal-radar\   # git clone; do not install into product venv as dependency
```

---

## 3. G2 — nse-oi-dashboard

**URL:** https://github.com/raghavs-stack/nse-oi-dashboard  
**What it is:** NSE Nifty/BankNifty **Live OI Dashboard** v5.5 — OI, PCR, max pain, IV analytics, Tkinter/Streamlit GUIs.  
**Data source (README):** **Shoonya (Finvasia) API** (not raw NSE Akamai path) — free for account holders; demo mode without login.

### Layout (from README)

```text
core/     market_hours, nse_fetcher, shoonya_client
signals/  indicators, oi_analytics, iv_analytics
display/  terminal, gui
backtest/ eod_backtest
```

### Useful if we hit build issues

| Area | Steal carefully |
|------|-----------------|
| OI analytics | PCR, max pain, support/resistance from OI walls → port formulas into `surface.py` / FO flow with our units |
| IV analytics | ATM IV, skew display ideas → map to our IV hierarchy (exchange→mid→LTP→unknown) |
| Dual OI tab UI | Template for **Index Dashboard** + **OI Tracker** |
| Market hours helper | IST session checks |
| CSV dumps / state JSON | Ideas for PIT archive of OI snapshots |
| Demo mode | Fixture-style offline UI while chain empty |

### Reject / quarantine from this repo

| Feature | Why |
|---------|-----|
| **4-factor bias voting** (PCR + OI + max pain + RSI/VWAP) | Dual/multi score → state; conflicts with one OPTIONS_PACKAGE + structure owns direction |
| Signal scorer 0–100 + MIN_SIGNAL_SCORE trade filter | Trade automation theater; no OMS; confidence ≠ P(win) |
| Shoonya as **only** feed for product gates | Broker API is separate boundary (like OpenAlgo); needs own validation; not inventory compiler default |
| Credentials / TOTP in product tree | Never commit secrets; keep out of TrendForge main config |
| Max pain as automatic trade target | Our law: reference + sensitivity only |

### Note vs our M10

Their path avoids NSE Akamai by using Shoonya. We may still use ideas if official `nse_option_chain` stays empty — but only as **optional unofficial comparison**, same class as OpenAlgo read-only, **never** gate authority alone.

---

## 4. G3 — Python-NSE-Option-Chain-Analyzer

**URL:** https://github.com/VarunS2002/Python-NSE-Option-Chain-Analyzer  
**What it is:** Mature desktop tool that pulls NSE option-chain page/API and analyzes CE/PE OI around a strike (Sameer Dharaskar–style teaching formulas).  
**License (badge):** **GPL v3** — copy carefully; GPL can force open-sourcing if linked tightly. Prefer **reimplement** formulas under our license, not paste whole app.  
**Stack:** Python, pandas, requests, brotli, tksheet, tkinter.

### Useful if we hit build issues

| Area | Steal carefully |
|------|-----------------|
| **NSE session / headers / brotli decode** | Highest value if our `nse_option_chain` stays `NO_DATA` / block page |
| Refresh loop without duplicate rows | Only append when server time/data changes |
| Chain dump to CSV | Aligns with our raw archive mindset |
| Strike ± N OI sum / boundary metrics | Descriptive fields for Strike Explorer (not “bullish writers” product copy) |
| Multi-instance index vs stock mode | UX for symbol + expiry pickers |
| Late server update warning | Stale banner ideas |

### Reject / quarantine from this repo

| Feature | Why |
|---------|-----|
| Auto “Open Interest: Bullish/Bearish” product labels | OI does not prove side/intent; rewrite as descriptive sums only |
| Default missing values to **0** on error | **Fails our fail-closed law** — must be UNKNOWN, not silent zero |
| Toast “Call ITM / Put ITM” as trade signal | Research tags only if kept |
| Unofficial NSE scraping as sole authority | Keep under inventory contract + lineage |

### GPL note

Before any substantial copy: legal/license review. Prefer **reading algorithms → rewrite in-house** under TrendForge licensing.

---

## 5. Fallback playbook (when our build breaks)

| Symptom | Try first (ours) | Then open repo |
|---------|------------------|----------------|
| Empty / blocked option chain | Session profile, fixture, M10 | **G3** session/headers/brotli; **G2** Shoonya only as optional comparison |
| No multi-name OI board | `nse_fo_bhavcopy` + spurts parsers | **G2** OI table layout; not their score |
| Index FO UI blank | live_equity_derivatives VERIFY M14 | **G2** dual OI tabs |
| Radar shell weak | discovery Mode A–E + headers | **G1** static dashboard layout |
| PCR / max pain display wrong | Our surface formulas + tests | **G2** `oi_analytics` / **G3** PCR sum math — reimplement |
| Rate limit / CAPTCHA | Budget + shortlist-only chain | Do **not** rotate fingerprints / bypass; fail-closed WAIT |

---

## 6. Integration rules (if we ever copy code)

1. **Pin** exact commit SHA; record in this file under “Pins used”.  
2. **License** check (esp. G3 GPL-3).  
3. Place experimental ports under e.g. `backend/trendforge_api/options_intelligence/_reference/` or external `reference/github/` — **not** on state path until tests pass.  
4. Adapter must emit our contracts: `status`, `reason`, `UNKNOWN` vs `0`, lineage, `snapshot_bundle_id`.  
5. CI test: **no import** of their score/SSI into gate or CONFIRMED path.  
6. UI copy: no win%, no auto entry/target as product truth.

### Pins used

| Repo | Commit / tag | Date pinned | Notes |
|------|--------------|-------------|-------|
| G1 et-signal-radar | *(not pinned yet)* | — | Clone on demand |
| G2 nse-oi-dashboard | *(not pinned yet)* | — | Clone on demand |
| G3 Python-NSE-Option-Chain-Analyzer | *(not pinned yet)* | latest known tag **v5.8** on releases | GPL-3 |

---

## 7. Path index

| Role | Path |
|------|------|
| **This file** | `D:\TrendForge\docs\GITHUB_OI_CHAIN_REFERENCE_REPOS.md` |
| Options canonical plan | `D:\TrendForge\docs\OPTIONS_INTELLIGENCE_PLAN.md` |
| Discovery + PK plan | `D:\TrendForge\docs\DISCOVERY_AND_PK_ENGINE_MILESTONE_PLAN.md` |
| Optional local clones | `D:\TrendForge\reference\github\` *(create when needed)* |

---

## 8. Quick clone commands (optional)

```bash
mkdir -p /d/TrendForge/reference/github
cd /d/TrendForge/reference/github
git clone https://github.com/krishnabhokare27/et-signal-radar.git
git clone https://github.com/raghavs-stack/nse-oi-dashboard.git
git clone https://github.com/VarunS2002/Python-NSE-Option-Chain-Analyzer.git
```

Do **not** add these as `pip install -e` product dependencies by default.

---

*Saved for build fallback. Official inventory + fail-closed contracts remain the spine.*
