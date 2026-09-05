"""List duplicate LINKED_SOURCES rows and the correct data link for each source_key."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pandas as pd

XLSX = Path(r"D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx")
OUT_DIR = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)


def score(item: dict) -> int:
    role = str(item.get("role") or "")
    url = str(item.get("url") or "").lower()
    s = 0
    if role == "OFFICIAL_OR_PRIMARY":
        s += 10
    elif role == "CONFIG_ENDPOINT_CONTRACT":
        s += 6
    elif role == "UNVERIFIED_RESEARCH":
        s += 4
    elif role == "CONFIG_SUPPORT_URL":
        s += 1
    if "api." in url or "/api/" in url:
        s += 5
    if any(x in url for x in (".csv", "bhavcopy", "fredgraph", ".zip", "json?")):
        s += 5
    if any(
        x in url
        for x in (
            "companies-listing",
            "/static/",
            "about/",
            "beta.bse",
            "h5_data",
            "otherdata",
        )
    ):
        s -= 3
    if role == "CONFIG_SUPPORT_URL":
        s -= 2
    return s


def main() -> None:
    ls = pd.read_excel(XLSX, sheet_name="LINKED_SOURCES")
    groups: dict[str, list[dict]] = defaultdict(list)

    for i, r in ls.iterrows():
        keys = [
            p.strip()
            for p in str(r.get("active_source_keys") or "")
            .replace("|", ",")
            .split(",")
            if p.strip()
        ]
        for k in keys:
            groups[k].append(
                {
                    "row": int(i) + 1,
                    "keys": r.get("active_source_keys"),
                    "url": r.get("canonical_url"),
                    "example": r.get("example_url"),
                    "role": r.get("source_role"),
                    "inventory_id": r.get("inventory_id"),
                }
            )

    dups = {k: v for k, v in groups.items() if len(v) >= 2}
    rows_out: list[dict] = []
    md: list[str] = [
        "# Duplicate links and correct data link",
        "",
        "Same `source_key` appears on more than one LINKED_SOURCES row.",
        "**CORRECT** = best official data URL (API/CSV preferred over support webpage).",
        "",
    ]

    print(f"Duplicate source keys: {len(dups)}")
    print()

    for k in sorted(dups.keys()):
        items = dups[k]
        ranked = sorted(items, key=score, reverse=True)
        correct = ranked[0]
        md.append(f"## {k} ({len(items)} rows)")
        md.append(f"- **CORRECT:** `{correct['url']}`")
        md.append(f"- correct inventory row: {correct['row']} | role: {correct['role']}")
        md.append("- **DUPLICATE / other rows:**")
        print(f"SOURCE: {k}")
        print(f"  CORRECT (row {correct['row']}): {correct['url']}")
        for it in ranked[1:]:
            md.append(
                f"  - row {it['row']} | {it['role']} | `{it['url']}`"
            )
            print(f"  DUPLICATE row {it['row']} ({it['role']}): {it['url']}")
            rows_out.append(
                {
                    "source_key": k,
                    "correct_row": correct["row"],
                    "correct_role": correct["role"],
                    "correct_url": correct["url"],
                    "duplicate_row": it["row"],
                    "duplicate_role": it["role"],
                    "duplicate_url": it["url"],
                }
            )
        md.append("")
        print()

    csv_path = OUT_DIR / "DUPLICATE_LINKS_AND_CORRECT.csv"
    md_path = OUT_DIR / "DUPLICATE_LINKS_AND_CORRECT.md"
    pd.DataFrame(rows_out).to_csv(csv_path, index=False)
    md_path.write_text("\n".join(md), encoding="utf-8")

    # also simple one-line table
    simple = []
    for k in sorted(dups.keys()):
        ranked = sorted(dups[k], key=score, reverse=True)
        simple.append(
            {
                "source_key": k,
                "times_listed": len(dups[k]),
                "correct_url": ranked[0]["url"],
                "duplicate_count": len(dups[k]) - 1,
                "duplicate_urls": " | ".join(str(x["url"]) for x in ranked[1:]),
            }
        )
    simple_path = OUT_DIR / "DUPLICATE_LINKS_SIMPLE.csv"
    pd.DataFrame(simple).to_csv(simple_path, index=False)

    print("WROTE", csv_path)
    print("WROTE", md_path)
    print("WROTE", simple_path)
    print("duplicate pair rows", len(rows_out))


if __name__ == "__main__":
    main()
