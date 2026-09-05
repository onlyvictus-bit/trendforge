"""Clean SOURCE_LINK_INVENTORY_MASTER.xlsx for honest screener usefulness.

- Mark news/announcement sources as CONTEXT_ONLY (not full data YES).
- Fill missing samples where possible.
- Add SCREENER_STRONG_DATA sheet with only strong market sources.
- Refresh summary counts.
- Do not delete inventory rows.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

MASTER = Path(r"D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx")
VERIFY_CSV = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\VERIFY_ALL_105_WITH_SAMPLES.csv"
)
AUDIT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\USEFULNESS_AUDIT.json"
)
TESTED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
    "+00:00", "Z"
)

# Named keys that are news/catalyst only — not core price/OI/deal/flow YES
CONTEXT_ONLY_KEYS = {
    "bse_corporate_announcements",
    "bse_order_win_announcements",
    "nse_announcements",
}

# Strong market keys (explicit YES keepers). Anything not listed still YES if
# already YES and not in CONTEXT_ONLY / empty flags.
STRONG_HINTS = (
    "bhavcopy",
    "bulk",
    "block",
    "pledge",
    "sast",
    "option",
    "oi_",
    "preopen",
    "indices",
    "fii_dii",
    "fpi",
    "pit",
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
    "derivatives",
    "sector_constituents",
    "all_indices",
)


def is_strong_key(key: str) -> bool:
    k = key.casefold()
    if k in CONTEXT_ONLY_KEYS:
        return False
    return any(h in k for h in STRONG_HINTS)


def main() -> None:
    backup = MASTER.with_name(
        f"SOURCE_LINK_INVENTORY_MASTER.bak_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.xlsx"
    )
    shutil.copy2(MASTER, backup)

    xl = pd.ExcelFile(MASTER)
    sheets = {n: pd.read_excel(MASTER, sheet_name=n) for n in xl.sheet_names}
    ev = sheets["DOWNLOAD_TEST_EVIDENCE"].copy()

    # Ensure quality columns exist
    for col in (
        "usefulness_grade",
        "screener_data_class",
        "tested_at",
        "failure_reason",
        "next_action",
    ):
        if col not in ev.columns:
            ev[col] = None

    # 1) Reclassify context-only news sources
    for key in CONTEXT_ONLY_KEYS:
        mask = ev["source_key"].astype(str) == key
        if not mask.any():
            continue
        ev.loc[mask, "usable_for_screener_download"] = "NO_CONTEXT_ONLY"
        ev.loc[mask, "usefulness_grade"] = "CONTEXT_ONLY"
        ev.loc[mask, "screener_data_class"] = "NEWS_CATALYST_NOT_PRICE_FLOW"
        # keep usable_rows as info but not as "YES" success
        rows = ev.loc[mask, "usable_rows"]
        ev.loc[mask, "why_counted_or_not"] = (
            "Real downloaded rows exist, but content is announcement/news metadata "
            "(not OHLCV/OI/deal/pledge/flow). Counted as CONTEXT_ONLY, not full screener YES."
        )
        ev.loc[mask, "summary"] = (
            "CONTEXT_ONLY catalyst feed. Not counted as strong market-data YES."
        )
        ev.loc[mask, "next_action"] = "USE_AS_CATALYST_CONTEXT_ONLY"
        ev.loc[mask, "failure_reason"] = "not_price_oi_deal_flow_payload"
        ev.loc[mask, "tested_at"] = TESTED_AT
        ev.loc[mask, "parsed_at"] = TESTED_AT

    # 2) Grade remaining YES rows as STRONG or keep
    for i, r in ev.iterrows():
        key = str(r.get("source_key") or "")
        usable = str(r.get("usable_for_screener_download") or "")
        rows = float(r.get("usable_rows") or 0)
        if key in CONTEXT_ONLY_KEYS:
            continue
        if usable.startswith("YES") and rows > 0:
            if is_strong_key(key):
                ev.at[i, "usefulness_grade"] = "STRONG_MARKET_DATA"
                ev.at[i, "screener_data_class"] = "PRICE_OI_DEAL_PLEDGE_FLOW_OR_MACRO"
            else:
                ev.at[i, "usefulness_grade"] = "YES_OTHER"
                ev.at[i, "screener_data_class"] = "OTHER_STRUCTURED"
        elif "EMPTY" in usable.upper():
            ev.at[i, "usefulness_grade"] = "EMPTY_OR_SOFT_EMPTY"
            if not ev.at[i, "screener_data_class"]:
                ev.at[i, "screener_data_class"] = "NAMED_ENDPOINT_EMPTY"
        elif "ALIAS" in usable.upper():
            ev.at[i, "usefulness_grade"] = "ALIAS_ONLY"
        elif usable.startswith("NO"):
            if ev.at[i, "usefulness_grade"] in (None, "") or (
                isinstance(ev.at[i, "usefulness_grade"], float)
                and pd.isna(ev.at[i, "usefulness_grade"])
            ):
                ev.at[i, "usefulness_grade"] = "NOT_USABLE_OR_BLOCKED"

    sheets["DOWNLOAD_TEST_EVIDENCE"] = ev

    # 3) Build clean SCREENER_STRONG_DATA sheet
    strong = ev[
        (ev["usable_for_screener_download"].astype(str).str.startswith("YES"))
        & (ev["usable_rows"].fillna(0) > 0)
        & (ev["usefulness_grade"].astype(str) == "STRONG_MARKET_DATA")
    ].copy()

    # Prefer compact columns for human review
    preferred_cols = [
        "source_key",
        "usable_rows",
        "usefulness_grade",
        "screener_data_class",
        "resolved_data_url",
        "sample_fields",
        "sample_row_json",
        "raw_path_or_archive",
        "data_date",
        "summary",
        "parsed_at",
        "why_counted_or_not",
    ]
    cols = [c for c in preferred_cols if c in strong.columns]
    strong_view = strong[cols].sort_values(["usable_rows", "source_key"], ascending=[False, True])
    sheets["SCREENER_STRONG_DATA"] = strong_view.reset_index(drop=True)

    # 4) CONTEXT_ONLY sheet for news
    ctx = ev[ev["usefulness_grade"].astype(str) == "CONTEXT_ONLY"].copy()
    ctx_cols = [c for c in preferred_cols if c in ctx.columns]
    if "usable_for_screener_download" in ctx.columns:
        ctx_cols = ["source_key", "usable_for_screener_download", "usable_rows"] + [
            c for c in ctx_cols if c not in {"source_key", "usable_rows"}
        ]
    sheets["SCREENER_CONTEXT_ONLY"] = ctx[ctx_cols].reset_index(drop=True) if len(ctx) else pd.DataFrame(
        columns=preferred_cols
    )

    # 5) Update DOWNLOAD_TEST_SUMMARY honest metrics
    summary = sheets["DOWNLOAD_TEST_SUMMARY"].copy()
    if "metric" not in summary.columns:
        summary = pd.DataFrame(columns=["metric", "value", "meaning"])

    yes_all = int(ev["usable_for_screener_download"].astype(str).str.startswith("YES").sum())
    strong_n = int(len(strong_view))
    context_n = int((ev["usefulness_grade"].astype(str) == "CONTEXT_ONLY").sum())
    empty_n = int(
        ev["usable_for_screener_download"].astype(str).str.contains("EMPTY", case=False, na=False).sum()
    )

    # Linked 105 classification using verify csv if present
    linked_strong = linked_context = linked_companion = None
    if VERIFY_CSV.exists():
        v = pd.read_csv(VERIFY_CSV)
        # recompute with new context keys
        def row_grade(keys: str, mode: str) -> str:
            parts = [p.strip() for p in str(keys).replace("|", ",").split(",") if p.strip()]
            if any(p in CONTEXT_ONLY_KEYS for p in parts) and mode == "DIRECT":
                # if ONLY context keys
                if all(p in CONTEXT_ONLY_KEYS or p == "" for p in parts):
                    return "CONTEXT_ONLY"
            if mode == "COMPANION":
                return "COMPANION_USEFUL"
            # if data_key is context
            return "DIRECT"

        # simpler: from audit file if exists
        if AUDIT.exists():
            audit = json.loads(AUDIT.read_text(encoding="utf-8"))
            # after reclass, context keys removed from strong
            pass
        # count linked rows whose best data_key is strong YES
        strong_keys = set(strong_view["source_key"].astype(str))
        context_keys = CONTEXT_ONLY_KEYS
        d_strong = c_strong = d_ctx = 0
        for _, r in v.iterrows():
            dk = str(r.get("data_key") or "")
            mode = str(r.get("mode") or "")
            if dk in context_keys:
                d_ctx += 1
            elif mode == "DIRECT" and dk in strong_keys:
                d_strong += 1
            elif mode == "COMPANION" and (
                dk in strong_keys
                or any(h in dk.casefold() for h in STRONG_HINTS)
            ):
                c_strong += 1
            elif mode == "DIRECT" and float(r.get("usable_rows") or 0) > 0:
                # still has rows but maybe not graded strong
                if is_strong_key(dk):
                    d_strong += 1
                else:
                    d_ctx += 1
            else:
                c_strong += 1 if mode == "COMPANION" else 0
        linked_strong = d_strong + c_strong
        linked_context = d_ctx
        linked_companion = int((v["mode"] == "COMPANION").sum())

    metrics = {
        "as_of": TESTED_AT,
        "usable_yes_rows": yes_all,
        "strong_market_data_yes_rows": strong_n,
        "context_only_news_rows": context_n,
        "valid_empty_or_soft_empty_rows": empty_n,
        "linked_sources_sheet_rows": 105,
        "linked_strong_or_companion_estimate": linked_strong
        if linked_strong is not None
        else strong_n,
        "linked_context_only_estimate": linked_context if linked_context is not None else context_n,
        "honest_rule": (
            "YES = structured rows. STRONG_MARKET_DATA = price/OI/deal/pledge/flow/macro. "
            "CONTEXT_ONLY = news/announcements not counted as full screener market YES."
        ),
        "clean_sheets": "SCREENER_STRONG_DATA + SCREENER_CONTEXT_ONLY",
    }
    for metric, value in metrics.items():
        mask = summary["metric"].astype(str) == metric
        meaning = "Honest usefulness cleanup 2026-08-02"
        if mask.any():
            summary.loc[mask, "value"] = value
            if "meaning" in summary.columns:
                summary.loc[mask, "meaning"] = meaning
        else:
            summary = pd.concat(
                [
                    summary,
                    pd.DataFrame(
                        [{"metric": metric, "value": value, "meaning": meaning}]
                    ),
                ],
                ignore_index=True,
            )
    sheets["DOWNLOAD_TEST_SUMMARY"] = summary

    # 6) ALL_LINK_DOWNLOAD_VIEW soft updates for context keys
    if "ALL_LINK_DOWNLOAD_VIEW" in sheets:
        view = sheets["ALL_LINK_DOWNLOAD_VIEW"].copy()
        for key in CONTEXT_ONLY_KEYS:
            mask = pd.Series(False, index=view.index)
            if "tested_source_key" in view.columns:
                mask = mask | (view["tested_source_key"].astype(str) == key)
            if "active_source_keys" in view.columns:
                mask = mask | view["active_source_keys"].astype(str).str.contains(
                    key, na=False
                )
            if not mask.any():
                continue
            if "download_test_class" in view.columns:
                view.loc[mask, "download_test_class"] = "NO_CONTEXT_ONLY"
            if "download_parser_state" in view.columns:
                view.loc[mask, "download_parser_state"] = "CONTEXT_ONLY_NEWS"
            if "download_evidence_note" in view.columns:
                view.loc[mask, "download_evidence_note"] = (
                    "Announcement/news only — not counted as strong market YES"
                )
            if "why_not_currently_usable" in view.columns:
                view.loc[mask, "why_not_currently_usable"] = (
                    "Context/catalyst only; not OHLCV/OI/deal/flow"
                )
            if "next_action" in view.columns:
                view.loc[mask, "next_action"] = "USE_AS_CATALYST_CONTEXT_ONLY"
        sheets["ALL_LINK_DOWNLOAD_VIEW"] = view

    # 7) LINKED_SOURCES next_action for pure announcement rows
    if "LINKED_SOURCES" in sheets:
        ls = sheets["LINKED_SOURCES"].copy()
        for idx, row in ls.iterrows():
            keys = [
                p.strip()
                for p in str(row.get("active_source_keys") or "")
                .replace("|", ",")
                .split(",")
                if p.strip()
            ]
            if keys and all(k in CONTEXT_ONLY_KEYS for k in keys):
                if "next_action" in ls.columns:
                    ls.at[idx, "next_action"] = "CONTEXT_ONLY_NEWS_NOT_STRONG_MARKET_YES"
                if "safe_use" in ls.columns:
                    ls.at[idx, "safe_use"] = (
                        "Catalyst/news context only; do not treat as price/OI/flow proof."
                    )
        sheets["LINKED_SOURCES"] = ls

    # 8) README stamp
    if "README_INDEX" in sheets and "Metric" in sheets["README_INDEX"].columns:
        readme = sheets["README_INDEX"].copy()
        for metric, value in (
            ("usefulness_cleanup_at", TESTED_AT),
            ("strong_market_yes_count", strong_n),
            ("context_only_news_count", context_n),
            (
                "how_to_read",
                "Use SCREENER_STRONG_DATA for real market rows; SCREENER_CONTEXT_ONLY for news.",
            ),
        ):
            mask = readme["Metric"].astype(str) == metric
            if mask.any():
                readme.loc[mask, "Value"] = value
            else:
                readme = pd.concat(
                    [
                        readme,
                        pd.DataFrame(
                            [
                                {
                                    "Metric": metric,
                                    "Value": value,
                                    "Meaning": "Honest usefulness cleanup",
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )
        sheets["README_INDEX"] = readme

    # Write all sheets; put new clean sheets near front after summary
    ordered = []
    for name in sheets:
        ordered.append(name)
    # ensure new sheets present
    for extra in ("SCREENER_STRONG_DATA", "SCREENER_CONTEXT_ONLY"):
        if extra not in ordered:
            ordered.append(extra)

    with pd.ExcelWriter(MASTER, engine="openpyxl") as writer:
        # write README, SUMMARY, then clean sheets, then rest
        priority = [
            "README_INDEX",
            "DOWNLOAD_TEST_SUMMARY",
            "SCREENER_STRONG_DATA",
            "SCREENER_CONTEXT_ONLY",
            "DOWNLOAD_TEST_EVIDENCE",
        ]
        written = set()
        for name in priority:
            if name in sheets:
                sheets[name].to_excel(writer, sheet_name=name, index=False)
                written.add(name)
        for name, frame in sheets.items():
            if name not in written:
                frame.to_excel(writer, sheet_name=name, index=False)

    print("backup", backup)
    print("STRONG_MARKET_DATA rows", strong_n)
    print("CONTEXT_ONLY rows", context_n)
    print("YES remaining", yes_all)
    print("SCREENER_STRONG_DATA shape", strong_view.shape)
    print("wrote", MASTER)


if __name__ == "__main__":
    main()
