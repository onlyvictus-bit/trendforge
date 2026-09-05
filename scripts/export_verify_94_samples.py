"""Export verification table for 94 DIRECT + 11 COMPANION linked rows with samples."""
from __future__ import annotations

import json
from collections import Counter  # noqa: F401 used in print
from pathlib import Path

import pandas as pd

ROOT = Path(r"D:\TrendForge")
XLSX = ROOT / "data/reports/SOURCE_LINK_INVENTORY_MASTER.xlsx"
OUT_DIR = ROOT / "data/raw_sources/verified_downloads/2026-08-01/full105"
OUT_DIR.mkdir(parents=True, exist_ok=True)

COMPANIONS = {
    "nse_option_chain_equity": "nse_live_equity_derivatives_stock_opt",
    "nse_option_chain": "nse_live_equity_derivatives_stock_opt",
    "nse_regulation_29": "bse_sast",
    "nse_regulation_31": "bse_pledge_data",
    "nse_block_deal": "nse_large_deals_snapshot",
    "nse_block_deal_live": "nse_large_deals_snapshot",
    "nsdl_fpi_fortnightly": "cdsl_fpi_fortnightly_sector",
    "nse_daily_buyback": "bse_buyback_tender",
    "nse_pit_current": "nse_pit_symbol",
    "nse_live_equity_derivatives": "nse_live_equity_derivatives_stock_opt",
    "nse_market_variations": "nse_variations_gainers",
}


def _sample_str(sample, limit: int = 220) -> str:
    if sample is None or (isinstance(sample, float) and pd.isna(sample)):
        return ""
    try:
        if isinstance(sample, str):
            obj = json.loads(sample)
        else:
            obj = sample
        return json.dumps(obj, ensure_ascii=False)[:limit]
    except Exception:
        return str(sample)[:limit]


def main() -> None:
    ls = pd.read_excel(XLSX, sheet_name="LINKED_SOURCES")
    ev = pd.read_excel(XLSX, sheet_name="DOWNLOAD_TEST_EVIDENCE")

    ev_map: dict[str, dict] = {}
    for _, r in ev.iterrows():
        k = str(r["source_key"])
        u = str(r.get("usable_for_screener_download") or "")
        rows = float(r.get("usable_rows") or 0)
        ev_map[k] = {
            "usable": u,
            "rows": int(rows) if rows == rows else 0,
            "sample": r.get("sample_row_json"),
            "fields": r.get("sample_fields"),
            "url": r.get("resolved_data_url") or r.get("catalog_url"),
            "raw": r.get("raw_path_or_archive"),
            "summary": r.get("summary") or r.get("why_counted_or_not"),
        }

    def key_status(k: str):
        e = ev_map.get(k)
        if e and str(e["usable"]).startswith("YES") and e["rows"] > 0:
            return "DIRECT", k, e
        ck = COMPANIONS.get(k)
        if ck:
            e2 = ev_map.get(ck)
            if e2 and str(e2["usable"]).startswith("YES") and e2["rows"] > 0:
                return "COMPANION", ck, e2
        return "NO", None, None

    direct_rows: list[dict] = []
    companion_rows: list[dict] = []
    for i, r in ls.iterrows():
        keys = [
            p.strip()
            for p in str(r.get("active_source_keys") or "")
            .replace("|", ",")
            .split(",")
            if p.strip()
        ]
        best = None
        for k in keys:
            st, dk, e = key_status(k)
            if st == "DIRECT":
                best = ("DIRECT", k, dk, e, r)
                break
        if best is None:
            for k in keys:
                st, dk, e = key_status(k)
                if st == "COMPANION":
                    best = ("COMPANION", k, dk, e, r)
                    break
        if best is None:
            continue
        mode, named, data_key, e, row = best
        item = {
            "row_no": int(i) + 1,
            "mode": mode,
            "source_keys": row.get("active_source_keys"),
            "data_key": data_key,
            "usable_rows": e["rows"],
            "url": e.get("url") or row.get("canonical_url"),
            "sample_fields": e.get("fields"),
            "sample_row": _sample_str(e.get("sample"), 400),
            "raw_path": e.get("raw"),
            "summary": str(e.get("summary") or "")[:240],
            "canonical_url": row.get("canonical_url"),
        }
        if mode == "DIRECT":
            direct_rows.append(item)
        else:
            companion_rows.append(item)

    all_rows = sorted(direct_rows + companion_rows, key=lambda x: x["row_no"])
    df = pd.DataFrame(all_rows)
    csv_path = OUT_DIR / "VERIFY_ALL_105_WITH_SAMPLES.csv"
    json_path = OUT_DIR / "VERIFY_ALL_105_WITH_SAMPLES.json"
    md_path = OUT_DIR / "VERIFY_ALL_105_WITH_SAMPLES.md"
    df.to_csv(csv_path, index=False)
    json_path.write_text(
        json.dumps(
            {
                "direct_count": len(direct_rows),
                "companion_count": len(companion_rows),
                "total": len(all_rows),
                "rows": all_rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Verification pack — show data for all 105 linked rows",
        "",
        f"- DIRECT: **{len(direct_rows)}**",
        f"- COMPANION: **{len(companion_rows)}**",
        f"- Total: **{len(all_rows)}**",
        "",
        "Sample rows come from `DOWNLOAD_TEST_EVIDENCE.sample_row_json` (saved from real downloads).",
        "",
        "## DIRECT (named key has rows)",
        "",
        "| # | source_keys | data_key | rows | sample |",
        "|--:|---|---|---:|---|",
    ]
    for r in sorted(direct_rows, key=lambda x: x["row_no"]):
        s = (r.get("sample_row") or "(no sample stored in evidence)").replace("|", "/")
        lines.append(
            f"| {r['row_no']} | {r['source_keys']} | {r['data_key']} | {r['usable_rows']} | `{s}` |"
        )

    lines += [
        "",
        "## COMPANION only (named empty; backup has rows)",
        "",
        "| # | source_keys | data_key used | rows | sample |",
        "|--:|---|---|---:|---|",
    ]
    for r in sorted(companion_rows, key=lambda x: x["row_no"]):
        s = (r.get("sample_row") or "(no sample stored in evidence)").replace("|", "/")
        lines.append(
            f"| {r['row_no']} | {r['source_keys']} | {r['data_key']} | {r['usable_rows']} | `{s}` |"
        )

    # unique keys section
    uniq = {}
    for r in all_rows:
        uniq.setdefault(r["data_key"], r)
    lines += ["", "## Unique data keys (easier to check downloads)", ""]
    for k, r in sorted(uniq.items()):
        lines.append(f"### {k} — {r['usable_rows']} rows ({r['mode']})")
        lines.append(f"- URL: {r.get('url')}")
        lines.append(f"- fields: {r.get('sample_fields')}")
        lines.append(f"- sample: `{r.get('sample_row')}`")
        lines.append(f"- raw: {r.get('raw_path')}")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("DIRECT", len(direct_rows))
    print("COMPANION", len(companion_rows))
    print("CSV", csv_path)
    print("JSON", json_path)
    print("MD", md_path)
    print("unique data keys", len(uniq))
    print("sample key counts", Counter(r["data_key"] for r in direct_rows).most_common(15))
    has_sample = sum(1 for r in direct_rows if r.get("sample_row"))
    print("direct with sample text", has_sample, "without", len(direct_rows) - has_sample)


if __name__ == "__main__":
    main()
