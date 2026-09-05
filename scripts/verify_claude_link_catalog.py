"""Verify Claude's per-link major fields + Top5 sort catalog against real samples."""
from __future__ import annotations

import json
from pathlib import Path

VERIFY = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\VERIFY_ALL_105_WITH_SAMPLES.json"
)
OUT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\CLAUDE_LINK_CATALOG_VERIFY.md"
)


def parse_sample(v):
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, str) and v.strip().startswith("{"):
        try:
            o = json.loads(v)
            return o if isinstance(o, dict) else {}
        except Exception:
            return {}
    return {}


def main() -> None:
    data = json.loads(VERIFY.read_text(encoding="utf-8"))
    rows = {int(r["row_no"]): r for r in data["rows"]}

    # (rows, key, claude_ok?, issue)
    checks = [
        # News
        ("1,9,32", "bse_corporate_announcements", "OK_NEWS", "News only; time DESC OK; not price Top5"),
        ("2", "bse_order_win_announcements", "OK_NEWS", "News only; time DESC OK"),
        ("54,89,90", "nse_announcements", "OK_NEWS", "News only; backups are same feed"),
        # Deals
        ("3,38", "bse_bulk_deals", "OK", "qty*price DESC OK when price+qty present"),
        ("4,11,37", "bse_block_deals", "OK", "BSE block has data; value sort OK"),
        ("8,98", "nse_large_deals", "OK", "deal value sort OK; sample may be missing in sheet"),
        ("53", "nse_block_deal", "WRONG_ALWAYS_TOP5", "Often VALID EMPTY; use large_deals_snapshot"),
        ("87", "nse_large_deals_snapshot", "OK_BUT_GROUP_WRONG", "Sort OK; Claude put under Ownership — should be Deals"),
        # Ownership
        ("5,6,33,35", "bse_sast", "CAUTION", "Sort by QTY OK; Value Rs may fail (no price often)"),
        ("7,10,34", "bse_pledge_data", "OK", "Encumbered % DESC OK"),
        ("55,93", "nse_pledge_data", "OK", "Encumbered qty/% sort OK"),
        ("56,57,58", "nse_shareholding_pattern", "CAUTION", "Ownership snapshot NOT buy/sell txn list"),
        ("59,94,95", "nse_regulation_29", "WRONG_ALWAYS_TOP5", "Often empty []; use BSE SAST"),
        ("60,96,97", "nse_regulation_31", "WRONG_ALWAYS_TOP5", "Often empty []; use BSE pledge"),
        ("64,92", "nse_pit_symbol", "OK", "Value DESC OK with wide date window"),
        # Commodity
        ("12,13", "sge_benchmark_gold", "OK_SERIES", "Date DESC OK; NOT stock Top5"),
        ("19,46", "wgc_gold_etf_holdings", "OK_SERIES", "Holdings ranking OK; not stocks"),
        ("20,47", "world_gold_council_oi", "OK_SERIES", "OI by venue OK; not stocks"),
        ("21,43", "eia_weekly_petroleum_stocks", "OK_SERIES", "Inventory %change OK; not stocks"),
        ("27", "cftc_legacy_futures_only", "OK_DISTINCT", "OI DESC OK; distinct from Disagg/TFF"),
        ("28", "cftc_disagg_futures_only", "OK_DISTINCT", "OI DESC OK; distinct feed"),
        ("29", "cftc_tff_futures_only", "OK_DISTINCT", "OI DESC OK; distinct feed"),
        ("40,41,42", "cftc_cot", "CAUTION", "Mixed zip/text/page under one key — not one identical Top5"),
        ("48,49", "mcx_bhavcopy", "OK", "Turnover/volume DESC OK for commodities"),
        # Flows
        ("14", "nsdl_fpi_daily", "OK_AGG", "Net flow by category OK; not stock list"),
        ("30,31", "amfi_scheme_wise", "CAUTION", "AUM sort may not match parser fields; often scheme/NAV"),
        ("44", "nsdl_fpi_fortnightly", "WRONG_ALWAYS_TOP5", "Often WAF blocked; CDSL is different source"),
        ("45", "nsdl_fpi_daily_reportdetail", "OK_AGG", "AUC category sort OK"),
        ("66,101", "nse_fii_dii", "OK_AGG", "Net FII/DII OK; not stock Top5"),
        # Macro
        ("15,17", "fred_real_yield_10y", "OK_SERIES", "Latest date OK; NOT stock gap board"),
        ("16,18", "fred_broad_dollar_index", "OK_SERIES", "Latest date OK; NOT stock list"),
        # Derivatives
        ("22,104", "nse_slb", "OK", "Open positions DESC OK"),
        ("25,51", "nse_fo_bhavcopy", "OK", "OI DESC OK for contracts"),
        ("71,99", "nse_oi_spurts_contracts", "OK", "OI change% DESC OK"),
        ("72", "nse_oi_spurts", "OK", "Underlying OI change% OK"),
        ("76", "banknifty_fut", "OK_DISTINCT", "Separate list; OI DESC OK"),
        ("77", "banknifty_opt", "OK_DISTINCT", "Separate list; OI walls OK"),
        ("78", "nifty_fut", "OK_DISTINCT", "Separate list"),
        ("79", "nifty_opt", "OK_DISTINCT", "Separate list"),
        ("80", "stock_fut", "OK_DISTINCT", "Separate list"),
        ("81", "stock_opt", "OK_DISTINCT", "Separate list; OI DESC OK"),
        ("82", "nse_preopen_fo", "CAUTION", "Gap/preopen board — NOT same as day gainers #73"),
        ("84", "nse_option_chain", "WRONG_ALWAYS_TOP5", "Often soft empty {}; cannot always show CE/PE Top5"),
        # Price universe
        ("23,50", "nse_bhavcopy_eod", "OK", "Top5 by traded value OK"),
        ("36,39", "bse_bhavcopy_eod", "OK", "Top5 by value OK"),
        ("24,103", "nse_equity_universe", "OK_NOT_MOVER", "Listing-date sort OK but not gap/volume movers"),
        # Regime
        ("26", "nse_nifty500_constituents", "OK_MEMBERSHIP", "Industry membership; not movers"),
        ("52", "nse_all_indices", "OK", "Index %change DESC OK"),
        ("61,88", "nse_corporate_filings_actions", "OK", "Ex-date ASC OK if fields present"),
        ("62,91", "nse_daily_buyback", "WRONG_ALWAYS_TOP5", "Often empty data=[]"),
        ("63", "nse_financial_results", "CAUTION", "Not dividend/split action table"),
        ("65", "nse_sector_constituents", "CAUTION", "Confirm schema; sample may be index-like not full stock OHLC"),
        ("67,102", "nse_trading_calendar", "OK_NOT_STOCKS", "Holiday list only"),
        ("68", "nse_most_active_value", "OK", "Value DESC OK"),
        ("69", "nse_most_active_volume", "OK", "Volume DESC OK"),
        ("70", "nse_most_active_underlying", "OK", "F&O turnover DESC OK"),
        ("73", "nse_variations_gainers", "OK", "%Change DESC = Top gainers"),
        ("74", "nse_variations_loosers", "OK", "%Change ASC = Top losers"),
        ("75", "nse_volume_gainers", "OK", "Spike from week avg fields OK"),
        ("83", "nse_market_turnover", "OK_NOT_STOCKS", "Segment totals only"),
        # Surveillance
        ("85,100", "nse_asm", "CAUTION", "Stage text needs rank map for true severity sort"),
        ("86,105", "nse_gsm", "CAUTION", "Stage text needs rank map"),
    ]

    # attach real usable_rows / sample keys
    rows = {int(r["row_no"]): r for r in json.loads(VERIFY.read_text(encoding="utf-8"))["rows"]}
    tallies: dict[str, int] = {}
    detail_lines = []
    for row_csv, key, verdict, note in checks:
        first = int(row_csv.split(",")[0])
        r = rows.get(first)
        usable = r.get("usable_rows") if r else "?"
        sample = parse_sample(r.get("sample_row") if r else None)
        sk = list(sample.keys())[:8]
        tallies[verdict] = tallies.get(verdict, 0) + 1
        detail_lines.append(
            f"| {row_csv} | `{key}` | {usable} | **{verdict}** | {note} | `{sk}` |"
        )
        print(f"{row_csv:12} | {key:36} | rows={usable} | {verdict:20} | {note}")

    md = f"""# Claude 105-link catalog verification

## Simple answer for you

Claude’s long list is **useful as a design map**, but **not 100% correct**.

Your need = **stock/contract name + unique numbers + Top 5** (gap up/down, volume, deals, etc.).

### Trust Claude for these boards
- Gainers / losers / volume gainers / most active / OI spurts
- BSE bulk & block deals (when rows exist)
- NSE large deals + **large deals snapshot**
- BSE/NSE pledge risk ranking
- PIT insider (symbol + wide dates)
- Live F&O lists **each separately** (stock/index opt/fut)
- Bhavcopy Top5 liquid names
- FII/DII & NSDL daily **category net flow** (not stock names)
- News: latest headlines only

### Do not trust “always Top 5 from this link”
| Link | Why |
|------|-----|
| #53 NSE block deal | Often empty session |
| #84 option chain | Often soft empty body |
| #59/94/95 reg29 | Often empty; use BSE SAST |
| #60/96/97 reg31 | Often empty; use BSE pledge |
| #62/91 daily buyback | Often empty |
| #44 NSDL fortnightly | Often blocked |
| #15–18 FRED | Not stocks — latest dates only |
| #12–13,19–21 gold/oil series | Not stock gap boards |

### Sort fixes
- **SAST**: sort by **qty**, not ₹ value (price often missing)
- **ASM/GSM**: stage needs a **rank map** (Stage IV > Stage I)
- **Shareholding**: not buy/sell insider list
- **Preopen (#82)**: gap board ≠ day gainers (#73)
- **#87**: move to **Deals** group (Claude put under Ownership)
- **Backup/mirror rows**: same data — show **once**, not many Top5s

### Tally of checked groups
`{tallies}`

## Detail table
| Rows | Key | usable_rows | Verdict | Note | sample keys |
|------|-----|-------------|---------|------|-------------|
""" + "\n".join(detail_lines)

    OUT.write_text(md, encoding="utf-8")
    print("\nTALLY", tallies)
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
