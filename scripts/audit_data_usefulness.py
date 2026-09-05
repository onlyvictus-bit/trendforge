"""Honest audit: is verification Excel actually useful screener data?"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

CSV = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\VERIFY_ALL_105_WITH_SAMPLES.csv"
)
XLSX = Path(r"D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx")
OUT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\USEFULNESS_AUDIT.json"
)

# Fields that count as real trading/screener value for TrendForge
STRONG = {
    "symbol",
    "scrip",
    "scripcode",
    "scrip_code",
    "open",
    "high",
    "low",
    "close",
    "ltp",
    "lastprice",
    "volume",
    "oi",
    "openinterest",
    "strike",
    "expiry",
    "optiontype",
    "quantity",
    "price",
    "pledge",
    "grosspurchases",
    "grosssales",
    "netinvestment",
    "buyvalue",
    "sellvalue",
    "netvalue",
    "isin",
    "underlying",
    "benchmark_value",
    "value",
    "tradedvalue",
    "client_name",
    "clientname",
    "transaction_type",
}
WEAK_META = {
    "newsid",
    "xml_name",
    "attfilesize",
    "filestatus",
    "chart30path",
    "identifier",
}


def classify(sample: object, fields: object, rows: int, key: str) -> tuple[str, str]:
    if rows is None or float(rows or 0) <= 0:
        return "NO_ROWS", "usable_rows is 0"
    text = f"{sample or ''} {fields or ''} {key}".casefold()
    strong_hits = [x for x in STRONG if x in text.replace(" ", "")]
    # normalize field names
    field_text = str(fields or "").casefold().replace(" ", "").replace(";", " ")
    strong_hits = list(
        {
            x
            for x in STRONG
            if x in text.replace(" ", "").replace("_", "") or x in field_text.replace("_", "")
        }
    )

    # Category-based judgment
    k = key.casefold()
    if any(
        x in k
        for x in (
            "bhavcopy",
            "bulk",
            "block",
            "pledge",
            "option",
            "oi_spurts",
            "preopen",
            "indices",
            "fii_dii",
            "fpi",
            "pit",
            "sast",
            "asm",
            "gsm",
            "slb",
            "participant",
            "mcx",
            "cftc",
            "fred",
            "eia",
            "sge",
            "gold",
            "equity_universe",
            "nifty500",
            "large_deals",
            "buyback",
            "variations",
            "volume_gainers",
            "most_active",
            "market_turnover",
            "financial_results",
            "shareholding",
            "corporate_filings",
            "trading_calendar",
            "amfi",
            "cdsl",
        )
    ):
        if rows > 0 and (strong_hits or "sample" not in str(sample).casefold()):
            # known market sources even if sample missing
            if strong_hits or str(sample) not in ("", "nan", "None"):
                return "USEFUL", f"market source key + rows={rows}; hits={strong_hits[:6]}"
            return "USEFUL_BUT_NO_SAMPLE", f"market source key but sample missing; rows={rows}"

    if "announcement" in k or "order_win" in k:
        if "scrip" in text or "scrip_cd" in text or "symbol" in text:
            return "CONTEXT_ONLY", "news/catalyst rows with company id — not OHLCV/flow"
        return "WEAK", "announcement without clear security fields"

    if strong_hits:
        return "USEFUL", f"hits={strong_hits[:8]}"
    if str(sample) in ("", "nan", "None") or sample is None:
        return "NO_SAMPLE", "rows>0 but no sample stored in evidence"
    return "WEAK_OR_UNCLEAR", f"sample does not clearly show market fields: {str(sample)[:80]}"


def main() -> None:
    df = pd.read_csv(CSV)
    ev = pd.read_excel(XLSX, sheet_name="DOWNLOAD_TEST_EVIDENCE")
    ls = pd.read_excel(XLSX, sheet_name="LINKED_SOURCES")

    results = []
    for _, r in df.iterrows():
        grade, reason = classify(
            r.get("sample_row"), r.get("sample_fields"), r.get("usable_rows"), str(r.get("data_key"))
        )
        results.append(
            {
                "row_no": int(r["row_no"]),
                "mode": r["mode"],
                "source_keys": r["source_keys"],
                "data_key": r["data_key"],
                "usable_rows": int(r["usable_rows"] or 0),
                "grade": grade,
                "reason": reason,
                "sample": str(r.get("sample_row") or "")[:200],
                "url": r.get("url"),
                "raw_path": r.get("raw_path"),
            }
        )
    out = pd.DataFrame(results)

    print("=== VERIFY CSV shape ===", df.shape)
    print("mode", df["mode"].value_counts().to_dict())
    print()
    print("=== USEFULNESS GRADES (honest) ===")
    print(out["grade"].value_counts().to_dict())
    print()

    useful = out[out["grade"].isin(["USEFUL", "USEFUL_BUT_NO_SAMPLE"])]
    context = out[out["grade"] == "CONTEXT_ONLY"]
    weak = out[out["grade"].isin(["WEAK", "WEAK_OR_UNCLEAR", "NO_SAMPLE", "NO_ROWS"])]

    print("LINKED ROWS with USEFUL market-ish data:", len(useful))
    print("  DIRECT useful:", len(useful[useful["mode"] == "DIRECT"]))
    print("  COMPANION useful:", len(useful[useful["mode"] == "COMPANION"]))
    print("CONTEXT_ONLY (news etc):", len(context))
    print("WEAK / NO_SAMPLE / unclear:", len(weak))
    print()

    print("--- CONTEXT_ONLY (not core OHLCV but may be catalyst) ---")
    for _, r in context.iterrows():
        print(f"{r['row_no']:3d} | {r['data_key'][:40]:40s} | {r['usable_rows']:5d} | {r['sample'][:100]}")

    print()
    print("--- WEAK / NO_SAMPLE ---")
    for _, r in weak.iterrows():
        print(f"{r['row_no']:3d} | {r['mode']:9s} | {r['data_key'][:34]:34s} | {r['grade']:18s} | {r['reason'][:80]}")

    # Evidence YES keys quality
    print()
    print("=== EVIDENCE SHEET YES keys ===")
    yes = ev[ev["usable_for_screener_download"].astype(str).str.startswith("YES")]
    print("YES keys", len(yes), "with rows>0", len(yes[yes["usable_rows"].fillna(0) > 0]))
    missing_sample = yes[
        yes["sample_row_json"].isna()
        | (yes["sample_row_json"].astype(str).str.strip().isin(["", "nan"]))
    ]
    print("YES but missing sample_row_json", len(missing_sample))
    for _, r in missing_sample.iterrows():
        print(f"  - {r['source_key']}: rows={r['usable_rows']}")

    # Spot-check a few raw files exist
    print()
    print("=== RAW FILE EXISTS? (sample of paths) ===")
    checked = 0
    missing_files = 0
    for _, r in out.head(30).iterrows():
        p = r.get("raw_path")
        if not p or str(p) in ("nan", "None"):
            continue
        path = Path(str(p))
        checked += 1
        ok = path.exists()
        if not ok:
            missing_files += 1
        print(f"{'OK' if ok else 'MISSING'} | {r['data_key'][:30]:30s} | {path}")
    print("checked", checked, "missing", missing_files)

    # Final honest summary for user POV
    summary = {
        "linked_rows_total": int(len(ls)),
        "verify_csv_rows": int(len(df)),
        "claimed_direct_94": int((df["mode"] == "DIRECT").sum()),
        "claimed_companion_11": int((df["mode"] == "COMPANION").sum()),
        "useful_marketish_rows": int(len(useful)),
        "context_only_rows": int(len(context)),
        "weak_or_no_sample_rows": int(len(weak)),
        "honest_note": (
            "Not every 'DIRECT' row is high-value OHLCV. "
            "Some are announcements (context). "
            "Some YES keys lack sample JSON in the sheet but have raw archives. "
            "94 means evidence says rows>0; usefulness is lower for news/meta."
        ),
        "grades": out["grade"].value_counts().to_dict(),
    }
    OUT.write_text(json.dumps({"summary": summary, "rows": results}, indent=2), encoding="utf-8")
    print()
    print("=== HONEST SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
