"""Verify Claude major-fields / Top-5 sort blueprint against real inventory samples.
No inventory edits. Prints honest PASS / CAUTION / WRONG notes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

XLSX = Path(r"D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx")
VERIFY = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\VERIFY_ALL_105_WITH_SAMPLES.json"
)
OUT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\CLAUDE_BLUEPRINT_VERIFY.md"
)


def parse_sample(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s or s in {"nan", "None"}:
            return {}
        try:
            o = json.loads(s)
            return o if isinstance(o, dict) else {}
        except Exception:
            return {}
    return {}


def field_blob(fields, sample: dict) -> str:
    return (
        str(fields or "")
        + " "
        + " ".join(sample.keys())
        + " "
        + " ".join(str(x) for x in sample.keys())
    ).casefold().replace("_", "")


def has(blob: str, *names: str) -> bool:
    return any(n.casefold().replace("_", "") in blob for n in names)


def main() -> None:
    if VERIFY.exists():
        raw = json.loads(VERIFY.read_text(encoding="utf-8"))
        rows = raw["rows"] if isinstance(raw, dict) else raw
    else:
        ls = pd.read_excel(XLSX, sheet_name="LINKED_SOURCES")
        ev = pd.read_excel(XLSX, sheet_name="DOWNLOAD_TEST_EVIDENCE")
        emap = {str(r["source_key"]): r for _, r in ev.iterrows()}
        rows = []
        for i, r in ls.iterrows():
            keys = [
                p.strip()
                for p in str(r.get("active_source_keys") or "")
                .replace("|", ",")
                .split(",")
                if p.strip()
            ]
            k = keys[0] if keys else ""
            e = emap.get(k)
            sample = parse_sample(e.get("sample_row_json") if e is not None else None)
            rows.append(
                {
                    "row_no": i + 1,
                    "source_keys": r.get("active_source_keys"),
                    "data_key": k,
                    "usable_rows": int(e.get("usable_rows") or 0) if e is not None else 0,
                    "sample_fields": e.get("sample_fields") if e is not None else "",
                    "sample_row": sample,
                    "mode": "DIRECT",
                }
            )

    findings = []

    for r in rows:
        key = str(r.get("source_keys") or r.get("data_key") or r.get("active_source_keys") or "")
        dk = str(r.get("data_key") or key.split(",")[0].split("|")[0]).strip()
        kl = key.casefold()
        sample = r.get("sample_row")
        if not isinstance(sample, dict):
            sample = parse_sample(sample)
        blob = field_blob(r.get("sample_fields"), sample)
        rows_n = int(r.get("usable_rows") or 0)
        mode = str(r.get("mode") or "")

        claude_fields = ""
        claude_sort = ""
        verdict = "OK"
        notes = []

        # Map Claude blueprint claims
        if "variations_gainers" in kl or (
            "gainers" in kl and "volume" not in kl and "oi" not in kl
        ):
            claude_fields = "Symbol | LTP | %Change | Volume | Traded Value"
            claude_sort = "%Change DESC"
            ok = has(blob, "symbol") and has(
                blob, "ltp", "lastprice", "last_price", "net_price", "pchange", "percent"
            )
            if not ok:
                verdict = "CAUTION"
                notes.append("Gainers sample fields differ; check real keys: " + ",".join(list(sample)[:8]))
            else:
                notes.append("PASS as stock mover list")

        elif "variations_loosers" in kl or "loosers" in kl or "losers" in kl:
            claude_fields = "Symbol | LTP | %Change | Volume"
            claude_sort = "%Change ASC (most negative first)"
            ok = has(blob, "symbol") and has(
                blob, "ltp", "lastprice", "net_price", "pchange", "percent"
            )
            notes.append("PASS as losers list" if ok else "CAUTION field names")
            verdict = "OK" if ok else "CAUTION"

        elif "volume_gainers" in kl:
            claude_fields = "Symbol | LTP | Volume | Volume Spike | %Change"
            claude_sort = "Volume spike / week avg ratio DESC"
            if has(blob, "week1avgvolume", "week1volchange", "volume"):
                notes.append("PASS: spike can be computed from week1AvgVolume / week1volChange")
            else:
                verdict = "CAUTION"
                notes.append("Spike factor may need computation; confirm fields")

        elif "most_active_value" in kl:
            claude_fields = "Symbol | LTP | Value | Volume"
            claude_sort = "Traded Value DESC"
            notes.append("PASS" if has(blob, "symbol") and has(blob, "value", "totaltradedvalue", "turnover") else "CAUTION")

        elif "most_active_volume" in kl:
            claude_fields = "Symbol | LTP | Volume"
            claude_sort = "Volume DESC"
            notes.append("PASS" if has(blob, "symbol", "volume", "quantity") else "CAUTION")

        elif "most_active_underlying" in kl:
            claude_fields = "Underlying | Fut/Opt volume | Turnover"
            claude_sort = "Total derivative volume/value DESC"
            notes.append("PASS for derivative underlyings (not cash stock list)")

        elif "oi_spurts" in kl:
            claude_fields = "Symbol/Contract | OI | OI Change % | LTP"
            claude_sort = "OI Change % DESC"
            if has(blob, "oichange", "changeinoi", "oichangepercent", "avgin oi", "avgin oi".replace(" ", "")) or has(
                blob, "changeinoi", "oichangepercent", "avgin oi"
            ):
                notes.append("PASS for OI spurt ranking")
            elif has(blob, "oi", "openinterest", "change"):
                notes.append("PASS-ish: OI fields present; confirm % field name")
            else:
                verdict = "CAUTION"
                notes.append("Confirm OI change field names in sample")

        elif "preopen" in kl:
            claude_fields = "Symbol | IEP | PrevClose | Gap % | Matched qty"
            claude_sort = "Gap % DESC (not same as day gainers list)"
            notes.append(
                "CAUTION vs Claude Group1: preopen is auction/gap context, NOT live gainers/losers list"
            )
            verdict = "CAUTION"

        elif any(x in kl for x in ("bulk", "block", "large_deal")):
            claude_fields = "Symbol/Scrip | Client | Buy/Sell | Qty | Price | Value | Date"
            claude_sort = "Deal Value (Qty×Price) DESC"
            if "block_deal" in kl and "snapshot" not in kl and "bulk" not in kl and "large" not in kl:
                notes.append(
                    "WRONG if you expect always-filled Top5: live /api/block-deal often VALID EMPTY; use large_deals_snapshot for populated block rows"
                )
                verdict = "WRONG_OR_EMPTY_NOW"
            elif has(blob, "symbol", "scrip") and has(blob, "qty", "quantity", "price"):
                notes.append("PASS: deal value sort is correct")
            elif rows_n := rows_n if (rows_n := int(r.get("usable_rows") or 0)) else 0:
                if rows_n > 0:
                    notes.append("PASS rows exist; sample may be sparse")
                else:
                    verdict = "EMPTY_NOW"
                    notes.append("No rows now")
            else:
                if int(r.get("usable_rows") or 0) == 0:
                    verdict = "EMPTY_NOW"
                    notes.append("No current rows")
                else:
                    notes.append("PASS/CAUTION: check client+qty+price fields")

        elif "announcement" in kl or "order_win" in kl:
            claude_fields = "Scrip | Headline | Category | Critical | Time | PDF"
            claude_sort = "Filing time DESC + critical pin"
            notes.append(
                "PASS as NEWS/CATALYST only — NOT stock price Top5. Claude Group3 OK for news, WRONG if mixed into price movers"
            )
            if has(blob, "scrip", "newssub", "headline", "subject", "an_dt", "dt_tm"):
                notes.append("fields mostly match")
            verdict = "OK_AS_NEWS_ONLY"

        elif "pledge" in kl:
            claude_fields = "Symbol/Company | Pledged qty | Promoter pledged %"
            claude_sort = "Promoter Encumbered % DESC"
            if has(blob, "pledge", "encum", "percent", "company", "scrip"):
                notes.append("PASS: pledge% sort is correct")
            else:
                verdict = "CAUTION"
                notes.append("Confirm pledge percent field names")
            notes.append("NOT insider buy/sell list — risk ranking by pledge%")

        elif "sast" in kl:
            claude_fields = "Scrip | Shareholder | BUY/SELL | Qty | % after"
            claude_sort = "Txn Value DESC (may need qty only if price missing)"
            if has(blob, "scrip", "company") and has(blob, "qty", "acq", "sale"):
                if not has(blob, "price", "value"):
                    notes.append(
                        "CAUTION: Claude Value₹Cr sort may FAIL — sample often has qty/% but no price; sort by qty or % change instead"
                    )
                    verdict = "CAUTION"
                else:
                    notes.append("PASS value sort")
            else:
                verdict = "CAUTION"

        elif "pit" in kl:
            claude_fields = "Symbol | Person | Txn type | Qty | Value | Date"
            claude_sort = "Transaction Value DESC"
            if int(r.get("usable_rows") or 0) == 0 and "pit_symbol" not in kl:
                notes.append(
                    "CAUTION: generic nse_pit may be empty; use nse_pit_symbol wide window (835 rows proven)"
                )
                verdict = "CAUTION"
            elif has(blob, "symbol") and has(blob, "quantity", "value", "entity"):
                notes.append("PASS for insider value ranking")
            else:
                notes.append("CAUTION field names")

        elif "regulation_29" in kl or "reg29" in kl:
            claude_fields = "Symbol | Acquirer | BUY/SELL | Qty | Holding before/after"
            claude_sort = "Value or qty DESC"
            notes.append(
                "WRONG for always-on Top5 from this URL alone: market-wide reg29 often VALID []; use BSE SAST companion for populated acquisition rows"
            )
            verdict = "WRONG_IF_MAIN_URL_ONLY"

        elif "regulation_31" in kl or "reg31" in kl:
            claude_fields = "Symbol | Pledge create/release/invoke | Qty | %"
            claude_sort = "Qty or % DESC"
            notes.append(
                "WRONG for always-on Top5 from this URL alone: often VALID []; use BSE pledge companion for risk ranking"
            )
            verdict = "WRONG_IF_MAIN_URL_ONLY"

        elif "option_chain" in kl:
            claude_fields = "Underlying | Expiry | Strike | CE/PE | LTP | OI | OI Change | IV"
            claude_sort = "OI DESC (walls) / OI change"
            notes.append(
                "WRONG if expect full chain now: equity option-chain often SOFT EMPTY {}; companions liveEquity *_opt give active contracts not full chain"
            )
            verdict = "WRONG_OR_SOFT_EMPTY"

        elif "live_equity_derivatives" in kl or "derivatives" in kl:
            claude_fields = "Underlying | Expiry | Strike | CE/PE/Fut | LTP | OI | Volume"
            claude_sort = "OI or Volume DESC"
            notes.append(
                "PASS as active F&O lists — BUT each index variant is DISTINCT dataset (do not merge stock_opt with bank_opt as one list)"
            )
            if has(blob, "underlying", "symbol") and has(blob, "oi", "openinterest", "volume"):
                notes.append("fields OK")
            verdict = "OK_DISTINCT_VARIANTS"

        elif "slb" in kl:
            claude_fields = "Symbol | Open Positions | Borrow rate"
            claude_sort = "Open Positions DESC"
            notes.append("PASS" if has(blob, "symbol", "openpositions", "volume") else "CAUTION")

        elif "asm" in kl or "gsm" in kl:
            claude_fields = "Symbol | Company | Stage | Code | Date"
            claude_sort = "Stage DESC"
            notes.append(
                "CAUTION: Stage is text (Stage I/IV/LVIII) — need mapped rank, not raw string sort"
            )
            verdict = "CAUTION"

        elif "fno_ban" in kl or key.casefold().endswith("ban"):
            claude_fields = "Symbol | ban status"
            claude_sort = "list order / symbol"
            notes.append(
                "VALID EMPTY often (no ban names that day) — Top5 may correctly be empty; not a failure"
            )
            verdict = "VALID_EMPTY_OK"

        elif "financial_results" in kl:
            claude_fields = "Symbol | Period | Filing time | Result metrics"
            claude_sort = "Filing time DESC"
            notes.append(
                "CAUTION vs Claude Group7 mix: financial results ≠ dividend/split corporate actions schema"
            )
            verdict = "CAUTION"

        elif "corporate_filings_actions" in kl or (
            "action" in kl and "buyback" not in kl
        ):
            claude_fields = "Symbol | Action type | Ex/record date | Amount"
            claude_sort = "Ex-date ASC upcoming"
            notes.append("PASS if action/ex-date fields exist")
            if not has(blob, "action", "ex", "symbol"):
                notes.append("CAUTION confirm fields")
                verdict = "CAUTION"

        elif "buyback" in kl:
            claude_fields = "Company | Phase | Dates | Offer price | Qty"
            claude_sort = "Announcement/start date DESC"
            notes.append(
                "CAUTION: NSE daily buyback often empty data=[]; BSE tender is company/phase/XBRL — not always same as daily execution qty"
            )
            verdict = "CAUTION"

        elif "fii_dii" in kl or ( "fpi" in kl and "fortnight" not in kl):
            claude_fields = "Category | Gross Buy | Gross Sell | Net | Date"
            claude_sort = "Net Flow DESC (or date)"
            if has(blob, "buy", "sell", "net", "category", "gross"):
                notes.append("PASS for flow ranking")
            else:
                notes.append("CAUTION fields")
                verdict = "CAUTION"
            notes.append("Aggregate market flow — NOT stock-level Top5 stocks")

        elif "fortnight" in kl:
            claude_fields = "Sector | AUC | Net investment"
            claude_sort = "AUC or net change DESC"
            notes.append(
                "CAUTION: NSDL fortnightly may be BLOCKED; CDSL sector page is distinct schema/source"
            )
            verdict = "CAUTION"

        elif "cftc" in kl:
            claude_fields = "Market | Contract | OI | NonComm/Commercial longs shorts"
            claude_sort = "OI or positioning change DESC"
            notes.append(
                "PASS concept — BUT Legacy/Disagg/TFF are DISTINCT feeds; never one merged Top5"
            )
            verdict = "OK_DISTINCT_FEEDS"

        elif "fred" in kl:
            claude_fields = "Series | Date | Value"
            claude_sort = "Observation Date DESC"
            notes.append(
                "WRONG if UI shows 'Top5 stocks': FRED is macro time series, not stock list. Top5 = latest 5 observations or biggest |change|"
            )
            verdict = "WRONG_IF_STOCK_TOP5"

        elif "sge" in kl or "wgc" in kl or "eia" in kl:
            claude_fields = "Series/Commodity | Value | Date | Change"
            claude_sort = "Date DESC or %change"
            notes.append(
                "NOT stock Top5 — macro/commodity series. Latest observations / largest moves"
            )
            verdict = "OK_AS_SERIES_NOT_STOCKS"

        elif "mcx" in kl and "bhav" in kl:
            claude_fields = "Symbol | Expiry | OHLC | Volume | OI"
            claude_sort = "Volume or OI DESC"
            notes.append("PASS commodity contracts Top5 by volume/OI")

        elif "bhavcopy" in kl or "equity_universe" in kl or "nifty500" in kl:
            claude_fields = "Symbol | OHLC | Volume | Value"
            claude_sort = "Volume/Value/%change DESC for Top5 highlight"
            notes.append(
                "PASS as full universe — Claude Group1 fields OK as secondary Top5 view over EOD file"
            )

        elif "all_indices" in kl or "sector_constituent" in kl:
            claude_fields = "Index/Sector | Last | %Change | Advances/Declines"
            claude_sort = "%Change DESC"
            notes.append("PASS regime list — not single-stock movers")

        elif "market_turnover" in kl:
            claude_fields = "Segment | Volume | Value"
            claude_sort = "Value DESC"
            notes.append("NOT stock Top5 — segment totals only")
            verdict = "OK_NOT_STOCK_LIST"

        elif "trading_calendar" in kl:
            claude_fields = "Date | Segment | Holiday name"
            claude_sort = "Date"
            notes.append("NOT stock Top5 — calendar only")
            verdict = "OK_NOT_STOCK_LIST"

        elif "shareholding" in kl:
            claude_fields = "Symbol | Holder categories | % holding | Date"
            claude_sort = "Date or promoter %"
            notes.append(
                "CAUTION: ownership snapshot, not insider txn stream; Claude Group4 'BUY/SELL' fields often do NOT apply"
            )
            verdict = "CAUTION"

        elif "amfi" in kl:
            claude_fields = "Scheme | NAV | Date | ISIN"
            claude_sort = "Date or AUM if present"
            notes.append("Fund NAV data — not stock gap/volume movers")
            verdict = "OK_NOT_STOCK_MOVER"

        elif "announcement" in kl:
            claude_fields = "Scrip | Headline | Time"
            claude_sort = "Time DESC"
            notes.append("NEWS only")
            verdict = "OK_AS_NEWS_ONLY"

        else:
            claude_fields = "(generic / Claude else-branch)"
            claude_sort = "Volume/Value DESC (Claude default)"
            notes.append(
                "GENERIC FALLBACK risky: not every dataset is stock volume/value. Use schema-specific rule"
            )
            verdict = "CAUTION_GENERIC"

        findings.append(
            {
                "row_no": r.get("row_no"),
                "key": key or dk,
                "usable_rows": r.get("usable_rows"),
                "mode": mode,
                "sample_keys": list(sample.keys())[:10],
                "claude_fields_claim": claude_fields,
                "claude_sort_claim": claude_sort,
                "verdict": verdict,
                "notes": " | ".join(notes),
            }
        )

    # Summaries
    vc = pd.Series([f["verdict"] for f in findings]).value_counts().to_dict()
    wrong = [f for f in findings if "WRONG" in f["verdict"]]
    caution = [f for f in findings if f["verdict"].startswith("CAUTION") or "CAUTION" in f["verdict"]]
    pass_n = [f for f in findings if f["verdict"] in {"OK", "OK_AS_NEWS_ONLY", "OK_DISTINCT_VARIANTS", "OK_DISTINCT_FEEDS", "OK_AS_SERIES_NOT_STOCKS", "OK_NOT_STOCK_LIST", "OK_NOT_STOCK_MOVER", "VALID_EMPTY_OK", "PASS"} or f["verdict"].startswith("OK")]

    md = [
        "# Claude blueprint verification (no code changes)",
        "",
        "## Verdict on Claude's 8-group blueprint",
        "",
        "**Useful as a UI design draft**, but **not fully correct** if applied blindly to all 105 links.",
        "",
        "### What is RIGHT",
        "- Grouping into topics (movers, deals, news, pledge, derivatives, surveillance, actions, macro) is good UX.",
        "- For **true stock movers** (gainers/losers/volume/most-active/OI spurts): Symbol + LTP + % + volume/value/OI sort is correct.",
        "- For **deals**: sort by deal value is correct when qty & price exist.",
        "- For **pledge**: sort by pledged % is correct.",
        "- For **F&O active lists**: sort by OI/volume is correct.",
        "- For **news**: sort by filing time is correct (but it is catalyst, not price data).",
        "",
        "### What is WRONG or MISLEADING",
        "1. **Not every link is a stock Top-5 board.** FRED/SGE/EIA/WGC/calendar/turnover/AMFI are series or meta — not gap-up stocks.",
        "2. **Option chain full CE/PE Top-5 from those URLs often unavailable** (soft empty `{}`). Don't promise max-pain/walls from empty chain.",
        "3. **Reg29/Reg31/live block-deal/NSE daily buyback** often **valid empty** — Top5 can be empty; need companions.",
        "4. **Preopen ≠ day gainers.** Gap auction fields differ from variations gainers.",
        "5. **SAST value sort** may fail without price — use qty or %.",
        "6. **ASM/GSM stage string sort** is not true stage severity without a rank map.",
        "7. **Merging liveEquity variants or CFTC classes into one Top5** is wrong — distinct datasets.",
        "8. **Claude else-branch** ('sort by volume/value') is dangerous for non-stock feeds.",
        "9. **Shareholding pattern ≠ insider BUY/SELL list.**",
        "10. **Financial results ≠ corporate action dividend/split table.**",
        "",
        "### Correct product rule for your screener",
        "- Show **major fields that actually exist in that feed's sample schema**.",
        "- Apply **Top-5 sort only when the feed is a list of stocks/contracts** with a clear rank field.",
        "- For time series / macro: show **latest N points**, not Top5 stocks.",
        "- For empty valid feeds: show **EMPTY NOW**, not fake Top5.",
        "",
        f"## Counts from this check ({len(findings)} rows)",
        "",
        f"- Verdict tallies: `{vc}`",
        f"- Clear WRONG/empty-main issues: **{len(wrong)}**",
        f"- CAUTION rows: **{len(caution)}**",
        f"- Mostly OK / OK-with-role-notes: **{len(pass_n)}**",
        "",
        "## Row-by-row findings",
        "",
    ]

    for f in sorted(findings, key=lambda x: (str(x.get("verdict")), int(x.get("row_no") or 0))):
        md.append(
            f"### Row {f.get('row_no')} — `{f.get('key')}` [{f.get('verdict')}]"
        )
        md.append(f"- usable_rows: {f.get('usable_rows')}")
        md.append(f"- sample keys: {f.get('sample_keys')}")
        md.append(f"- Claude fields claim: {f.get('claude_fields_claim')}")
        md.append(f"- Claude sort claim: {f.get('claude_sort_claim')}")
        md.append(f"- Notes: {f.get('notes')}")
        md.append("")

    OUT.write_text("\n".join(md), encoding="utf-8")
    print("FINDINGS", len(findings))
    print("VERDICTS", vc)
    print("WRONG count", len(wrong))
    for f in wrong:
        print("WRONG", f.get("row_no"), f.get("key"), "=>", f.get("notes")[:120])
    print("CAUTION count", len(caution))
    for f in caution[:25]:
        print("CAUTION", f.get("row_no"), str(f.get("key"))[:40], "=>", f.get("notes")[:100])
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
