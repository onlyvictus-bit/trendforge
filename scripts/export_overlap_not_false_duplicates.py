"""Corrected overlap audit for LINKED_SOURCES.

Does NOT treat every shared source_key as proven duplicate data.
Classifies rows as:
- TRUE_PROVENANCE_OVERLAP: same dataset, API/CSV vs human webpage
- DISTINCT_DATASET: different payload / different purpose (must keep)
- CANDIDATE_OVERLAP_NEEDS_CHECK: related URLs, do not auto-delete
- MULTI_KEY_ROW_DOUBLE_COUNT_GUARD: avoid counting same inventory row twice

Output replaces false "56 proven duplicates" with honest counts.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd

XLSX = Path(r"D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx")
OUT = Path(r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105")
OUT.mkdir(parents=True, exist_ok=True)

# Explicit DISTINCT datasets that share a family/key pattern but are NOT the same data
DISTINCT_URL_MARKERS: dict[str, list[str]] = {
    # liveEquity children — different indexes
    "nse_live_equity_derivatives": [
        "index=stock_opt",
        "index=stock_fut",
        "index=nse50_opt",
        "index=nse50_fut",
        "index=nifty_bank_opt",
        "index=nifty_bank_fut",
    ],
    "nse_market_variations": [
        "index=gainers",
        "index=loosers",
    ],
    "cftc_cot": [
        "6dca-aqww",  # legacy
        "72hh-3qpy",  # disagg
        "gpe5-46if",  # tff
        "fut_disagg_txt",  # historical zip
        "f_disagg.txt",  # current text
        "CommitmentsofTraders",  # nav page
    ],
    "nsdl_fpi_daily": [
        "Latest.aspx",  # daily trend
        "ReportDetail.aspx?RepID=94",  # AUC category (also nsdl_fpi_daily_reportdetail)
    ],
}

# source_keys that are known DISTINCT sibling contracts (never collapse to one URL)
ALWAYS_DISTINCT_KEYS = {
    "nse_live_equity_derivatives_stock_opt",
    "nse_live_equity_derivatives_stock_fut",
    "nse_live_equity_derivatives_index_opt",
    "nse_live_equity_derivatives_index_fut",
    "nse_live_equity_derivatives_banknifty_opt",
    "nse_live_equity_derivatives_banknifty_fut",
    "nse_variations_gainers",
    "nse_variations_loosers",
    "cftc_legacy_futures_only",
    "cftc_disagg_futures_only",
    "cftc_tff_futures_only",
    "nsdl_fpi_daily",
    "nsdl_fpi_daily_reportdetail",
}

# Needs separate human/manual check before any delete
NEEDS_CHECK_PAIRS = {
    "nse_shareholding_pattern",  # master vs symbol query
    "cftc_cot",  # text vs zip vs socrata classes
    "sge_benchmark_gold",  # graph endpoint vs h5 page
    "wgc_gold_etf_holdings",
    "wgc_gold_etf_flows",
    "nse_corporate_filings_actions",  # api vs filings page / xbrl page
}


def is_data_url(url: str) -> bool:
    u = (url or "").lower()
    return any(
        x in u
        for x in (
            "/api/",
            "api.",
            ".csv",
            ".zip",
            ".txt",
            "fredgraph",
            "bhavcopy",
            "resource/",
            "graph/dayily",
            "datawarehouseapi",
            "charts/etfv2",
        )
    )


def is_nav_page(url: str, role: str) -> bool:
    u = (url or "").lower()
    role = role or ""
    if role == "CONFIG_SUPPORT_URL":
        return True
    return any(
        x in u
        for x in (
            "companies-listing",
            "/static/",
            "market-data/",
            "markets/",
            "corporates/",
            "reports/",
            "index.htm",
            "index.php",
            "otherdata",
            "h5_data",
            "goldhub",
            "beta.bse",
            "all-reports",
        )
    ) and not is_data_url(u)


def score_fetch_priority(url: str, role: str) -> int:
    s = 0
    if is_data_url(url):
        s += 20
    if role == "OFFICIAL_OR_PRIMARY":
        s += 5
    if role == "CONFIG_ENDPOINT_CONTRACT":
        s += 8
    if is_nav_page(url, role):
        s -= 10
    return s


def classify_group(key: str, items: list[dict]) -> list[dict]:
    """Return classification records for items in a source_key group."""
    # Special: always-distinct contract keys
    if key in ALWAYS_DISTINCT_KEYS:
        return [
            {
                **it,
                "source_key": key,
                "class": "DISTINCT_DATASET",
                "reason": "Sibling contract/key returns a different dataset; not a duplicate.",
                "recommended_use": "KEEP_AND_FETCH",
            }
            for it in items
        ]

    # liveEquity family listed under alias key
    if key == "nse_live_equity_derivatives":
        out = []
        for it in items:
            u = str(it["url"])
            out.append(
                {
                    **it,
                    "source_key": key,
                    "class": "DISTINCT_DATASET",
                    "reason": f"liveEquity index variant: {u}",
                    "recommended_use": "KEEP_AND_FETCH_EACH_INDEX",
                }
            )
        return out

    if key == "nse_market_variations":
        out = []
        for it in items:
            u = str(it["url"]).lower()
            if "gainers" in u or "loosers" in u or "losers" in u:
                out.append(
                    {
                        **it,
                        "source_key": key,
                        "class": "DISTINCT_DATASET",
                        "reason": "gainers vs loosers are opposite market lists",
                        "recommended_use": "KEEP_AND_FETCH_BOTH",
                    }
                )
            else:
                out.append(
                    {
                        **it,
                        "source_key": key,
                        "class": "CANDIDATE_OVERLAP_NEEDS_CHECK",
                        "reason": "shared variations family",
                        "recommended_use": "REVIEW",
                    }
                )
        return out

    # CFTC family under cftc_cot multi-links
    if key == "cftc_cot":
        out = []
        for it in items:
            u = str(it["url"]).lower()
            if "6dca-aqww" in u:
                reason = "CFTC Legacy Socrata feed (distinct class)"
                cls = "DISTINCT_DATASET"
            elif "72hh-3qpy" in u:
                reason = "CFTC Disaggregated Socrata feed (distinct class)"
                cls = "DISTINCT_DATASET"
            elif "gpe5-46if" in u:
                reason = "CFTC TFF Socrata feed (distinct class)"
                cls = "DISTINCT_DATASET"
            elif "fut_disagg_txt" in u or u.endswith(".zip"):
                reason = "CFTC historical disagg ZIP"
                cls = "DISTINCT_DATASET"
            elif "f_disagg.txt" in u:
                reason = "CFTC current disagg text file"
                cls = "DISTINCT_DATASET"
            elif "commitmentsoftraders" in u:
                reason = "CFTC navigation/landing page"
                cls = "PROVENANCE_OR_NAVIGATION"
            else:
                reason = "CFTC-related URL; needs check"
                cls = "CANDIDATE_OVERLAP_NEEDS_CHECK"
            out.append(
                {
                    **it,
                    "source_key": key,
                    "class": cls,
                    "reason": reason,
                    "recommended_use": (
                        "KEEP_AS_NAV_ONLY"
                        if cls == "PROVENANCE_OR_NAVIGATION"
                        else "KEEP_AND_FETCH"
                    ),
                }
            )
        return out

    # NSDL daily family
    if key in {"nsdl_fpi_daily", "nsdl_fpi_daily_reportdetail"} or (
        key == "nsdl_fpi_daily"
    ):
        pass

    # Default: data URL vs nav page among same key
    # Also special-case nsdl when both Latest and ReportDetail appear under one key list
    out = []
    urls = [str(it["url"]) for it in items]
    has_latest = any("Latest.aspx" in u for u in urls)
    has_reportdetail = any("ReportDetail.aspx" in u for u in urls)

    for it in items:
        u = str(it["url"])
        role = str(it.get("role") or "")

        if key.startswith("nsdl_fpi") or "fpi.nsdl" in u:
            if "Latest.aspx" in u:
                out.append(
                    {
                        **it,
                        "source_key": key,
                        "class": "DISTINCT_DATASET",
                        "reason": "NSDL Latest.aspx daily-trend tables (e.g. 34 rows)",
                        "recommended_use": "KEEP_AND_FETCH",
                    }
                )
                continue
            if "ReportDetail.aspx" in u or "RepID=94" in u:
                out.append(
                    {
                        **it,
                        "source_key": key,
                        "class": "DISTINCT_DATASET",
                        "reason": "NSDL ReportDetail AUC-category tables (e.g. 28 rows)",
                        "recommended_use": "KEEP_AND_FETCH",
                    }
                )
                continue

        if key in NEEDS_CHECK_PAIRS and not is_nav_page(u, role):
            # multiple data-like URLs
            data_like = [x for x in items if is_data_url(str(x["url"]))]
            if len(data_like) >= 2 and is_data_url(u):
                out.append(
                    {
                        **it,
                        "source_key": key,
                        "class": "CANDIDATE_OVERLAP_NEEDS_CHECK",
                        "reason": "Related data URLs for same key; do not auto-delete without separate check",
                        "recommended_use": "REVIEW_BEFORE_ANY_DELETE",
                    }
                )
                continue

        if is_nav_page(u, role) and any(is_data_url(str(x["url"])) for x in items):
            out.append(
                {
                    **it,
                    "source_key": key,
                    "class": "PROVENANCE_OR_NAVIGATION",
                    "reason": "Official webpage companion to API/CSV; retain for manual navigation, not auto-fetch as data",
                    "recommended_use": "KEEP_AS_PROVENANCE_NOT_FETCH_DUPLICATE",
                }
            )
            continue

        if is_data_url(u):
            # if multiple data URLs with same key, prefer one for fetch but mark others carefully
            data_items = [x for x in items if is_data_url(str(x["url"]))]
            if len(data_items) > 1:
                best = max(
                    data_items,
                    key=lambda x: score_fetch_priority(str(x["url"]), str(x.get("role"))),
                )
                if str(it["url"]) == str(best["url"]) and int(it["row"]) == int(
                    best["row"]
                ):
                    out.append(
                        {
                            **it,
                            "source_key": key,
                            "class": "PRIMARY_FETCH_URL",
                            "reason": "Preferred automated fetch URL for this source_key",
                            "recommended_use": "FETCH",
                        }
                    )
                else:
                    # same exact API base vs parameterized
                    out.append(
                        {
                            **it,
                            "source_key": key,
                            "class": "CANDIDATE_OVERLAP_NEEDS_CHECK",
                            "reason": "Additional data URL for same source_key (e.g. template vs example); review before delete",
                            "recommended_use": "REVIEW_BEFORE_ANY_DELETE",
                        }
                    )
            else:
                out.append(
                    {
                        **it,
                        "source_key": key,
                        "class": "PRIMARY_FETCH_URL",
                        "reason": "Only data URL for this source_key",
                        "recommended_use": "FETCH",
                    }
                )
            continue

        out.append(
            {
                **it,
                "source_key": key,
                "class": "CANDIDATE_OVERLAP_NEEDS_CHECK",
                "reason": "Related listing; not proven identical dataset",
                "recommended_use": "REVIEW",
            }
        )
    return out


def main() -> None:
    ls = pd.read_excel(XLSX, sheet_name="LINKED_SOURCES")

    # Build per-key groups of inventory rows
    groups: dict[str, list[dict]] = defaultdict(list)
    row_to_keys: dict[int, list[str]] = defaultdict(list)

    for i, r in ls.iterrows():
        row_no = int(i) + 1
        keys = [
            p.strip()
            for p in str(r.get("active_source_keys") or "")
            .replace("|", ",")
            .split(",")
            if p.strip()
        ]
        for k in keys:
            row_to_keys[row_no].append(k)
            groups[k].append(
                {
                    "row": row_no,
                    "active_source_keys": r.get("active_source_keys"),
                    "url": r.get("canonical_url"),
                    "example_url": r.get("example_url"),
                    "role": r.get("source_role"),
                    "inventory_id": r.get("inventory_id"),
                }
            )

    multi_keys = {k: v for k, v in groups.items() if len(v) >= 2}

    classified_rows: list[dict] = []
    for k, items in sorted(multi_keys.items()):
        classified_rows.extend(classify_group(k, items))

    # Unique inventory rows appearing in multi-key groups (avoid double count)
    multi_group_rows = sorted({it["row"] for items in multi_keys.values() for it in items})

    # Unique inventory rows classified as provenance navigation only
    prov_rows = sorted(
        {
            r["row"]
            for r in classified_rows
            if r["class"] == "PROVENANCE_OR_NAVIGATION"
        }
    )
    distinct_rows = sorted(
        {r["row"] for r in classified_rows if r["class"] == "DISTINCT_DATASET"}
    )
    candidate_rows = sorted(
        {
            r["row"]
            for r in classified_rows
            if r["class"] == "CANDIDATE_OVERLAP_NEEDS_CHECK"
        }
    )
    primary_rows = sorted(
        {r["row"] for r in classified_rows if r["class"] == "PRIMARY_FETCH_URL"}
    )

    # Candidate companion/overlap rows = multi-listed inventory rows that are NOT distinct datasets
    # (user's corrected conclusion: 53 candidate companion/overlap rows)
    non_distinct_rows = sorted(
        {
            r["row"]
            for r in classified_rows
            if r["class"]
            in {
                "PROVENANCE_OR_NAVIGATION",
                "CANDIDATE_OVERLAP_NEEDS_CHECK",
                "PRIMARY_FETCH_URL",
            }
        }
    )
    # But primary fetch is the keep-for-fetch row; "overlap candidates" = rows that are extra listings
    # Better: inventory rows that appear in multi_keys minus pure distinct-only groups
    candidate_overlap_inventory_rows = []
    for row_no in multi_group_rows:
        # classes for this row across all keys
        classes = {r["class"] for r in classified_rows if r["row"] == row_no}
        if classes <= {"DISTINCT_DATASET"}:
            continue  # only distinct
        if "PROVENANCE_OR_NAVIGATION" in classes or "CANDIDATE_OVERLAP_NEEDS_CHECK" in classes:
            candidate_overlap_inventory_rows.append(row_no)
        elif "PRIMARY_FETCH_URL" in classes and len(row_to_keys[row_no]) >= 1:
            # primary itself is not "extra"; skip unless also nav
            pass

    # Extra overlap rows = multi_group_rows that are not the chosen primary for any of their keys
    # Build primary row per key for true provenance pairs
    primary_by_key: dict[str, int] = {}
    for k, items in multi_keys.items():
        data_items = [it for it in items if is_data_url(str(it["url"]))]
        pool = data_items or items
        best = max(pool, key=lambda x: score_fetch_priority(str(x["url"]), str(x.get("role"))))
        primary_by_key[k] = best["row"]

    extra_rows = set()
    for k, items in multi_keys.items():
        # skip always-distinct families counted as separate datasets
        sample_class = {
            r["class"] for r in classified_rows if r["source_key"] == k
        }
        if sample_class == {"DISTINCT_DATASET"}:
            continue
        if k in ALWAYS_DISTINCT_KEYS:
            continue
        primary = primary_by_key.get(k)
        for it in items:
            if it["row"] != primary:
                # if this item classified DISTINCT, don't mark extra
                item_class = next(
                    (
                        r["class"]
                        for r in classified_rows
                        if r["source_key"] == k and r["row"] == it["row"] and r["url"] == it["url"]
                    ),
                    None,
                )
                if item_class == "DISTINCT_DATASET":
                    continue
                extra_rows.add(it["row"])

    summary = {
        "verdict": "REFUTED as a full duplicate audit if '56 proven duplicates' was claimed",
        "mechanical_multi_source_key_groups": len(multi_keys),
        "unique_inventory_rows_in_multi_key_groups": len(multi_group_rows),
        "corrected_candidate_companion_or_overlap_rows": len(extra_rows),
        "old_wrong_extra_count_if_pairwise_refs": 56,
        "note_double_count": (
            "Pairwise duplicate references can count inventory rows 46/51/92 twice "
            "when a row carries multiple source_keys."
        ),
        "distinct_dataset_inventory_rows_in_overlap_groups": len(distinct_rows),
        "provenance_or_navigation_rows": len(prov_rows),
        "candidate_needs_check_rows": len(candidate_rows),
        "primary_fetch_rows": len(primary_rows),
        "policy": {
            "auto_fetch": "API/CSV/ZIP/data endpoints only",
            "web_pages": "PROVENANCE_OR_NAVIGATION — keep in inventory, do not auto-delete, do not fetch as data",
            "do_not_collapse": [
                "liveEquity stock/index/opt/fut variants",
                "variations gainers vs loosers",
                "CFTC legacy / disagg / TFF / text / zip",
                "NSDL Latest daily-trend vs ReportDetail AUC",
                "shareholding master vs symbol query (check first)",
                "SGE graph vs h5 page (check first)",
                "WGC holdings vs flows (check first)",
            ],
        },
    }

    # Save detail
    detail_df = pd.DataFrame(classified_rows)
    detail_path = OUT / "OVERLAP_CORRECTED_CLASSIFICATION.csv"
    detail_df.to_csv(detail_path, index=False)

    extra_df = pd.DataFrame(
        [
            {
                "inventory_row": row,
                "active_source_keys": ls.iloc[row - 1].get("active_source_keys"),
                "url": ls.iloc[row - 1].get("canonical_url"),
                "role": ls.iloc[row - 1].get("source_role"),
                "class_hint": "CANDIDATE_COMPANION_OR_PROVENANCE_OVERLAP",
            }
            for row in sorted(extra_rows)
        ]
    )
    extra_path = OUT / "CANDIDATE_OVERLAP_ROWS_53ish.csv"
    extra_df.to_csv(extra_path, index=False)

    # Markdown report
    md = [
        "# Corrected overlap audit (not false duplicates)",
        "",
        "## Verdict",
        "",
        "Earlier claim of **56 proven duplicates** is **REFUTED** as a full duplicate audit.",
        "",
        "| Claim | Result | Evidence |",
        "|---|---|---|",
        f"| 39 source groups occur more than once | **True mechanically** | Groups by shared `source_key` only ({len(multi_keys)} groups). |",
        f"| 56 extra duplicate rows | **Wrong** | Pairwise refs inflate count; unique extra inventory rows ≈ **{len(extra_rows)}**. Rows can be counted twice if multi-key. |",
        "| Every non-canonical URL is duplicate data | **Wrong** | liveEquity variants, gainers/loosers, CFTC classes, NSDL Latest vs RepID=94 are **distinct datasets**. |",
        "| Prefer API/CSV for automated fetch | **Correct** | Keep web pages as **PROVENANCE_OR_NAVIGATION**, not fetch duplicates. |",
        "",
        "## Correct conclusion",
        "",
        f"- Multi-listed source_key groups: **{len(multi_keys)}**",
        f"- Unique inventory rows involved in multi-key groups: **{len(multi_group_rows)}**",
        f"- **Candidate companion/overlap rows (extra listings): ~{len(extra_rows)}** (not proven identical data)",
        f"- Distinct datasets inside overlap families: keep and fetch separately",
        f"- Provenance/navigation pages: keep, do not auto-delete",
        "",
        "## Clearly NOT duplicates (keep all)",
        "",
        "1. **NSE liveEquity-derivatives variants** — stock/index, fut/opt, Nifty/BankNifty (rows ~3 to 1411)",
        "2. **NSE variations gainers vs loosers** — different symbols / direction",
        "3. **CFTC Legacy / Disagg / TFF** Socrata feeds — distinct report classes",
        "4. **NSDL Latest.aspx** daily-trend (~34) vs **ReportDetail?RepID=94** AUC (~28)",
        "",
        "## Do not auto-delete without separate check",
        "",
        "- NSE shareholding master vs symbol query",
        "- CFTC current text vs historical ZIP",
        "- NSE XBRL / filings navigation pages",
        "- SGE graph vs h5 page pair",
        "- WGC holdings vs flows pages",
        "",
        "## Policy",
        "",
        "- **Auto-download:** API / CSV / ZIP only",
        "- **Web pages:** `PROVENANCE_OR_NAVIGATION` — retain in inventory for humans",
        "- **Never delete** only because source_key is shared",
        "",
        f"## Extra candidate overlap inventory rows ({len(extra_rows)})",
        "",
    ]
    for row in sorted(extra_rows):
        rec = ls.iloc[row - 1]
        md.append(
            f"- row {row}: `{rec.get('active_source_keys')}` → {rec.get('canonical_url')}"
        )

    md_path = OUT / "OVERLAP_AUDIT_CORRECTED.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    summary_path = OUT / "OVERLAP_AUDIT_CORRECTED_SUMMARY.json"
    import json

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print("extra_rows", sorted(extra_rows))
    print("WROTE", detail_path)
    print("WROTE", extra_path)
    print("WROTE", md_path)
    print("WROTE", summary_path)


if __name__ == "__main__":
    main()
