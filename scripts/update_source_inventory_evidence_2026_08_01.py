"""Update SOURCE_LINK_INVENTORY_MASTER.xlsx DOWNLOAD_TEST_EVIDENCE with focus-fix results.

Does not create a new master inventory. Updates existing sheets only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

MASTER = Path(r"D:\TrendForge\data\reports\SOURCE_LINK_INVENTORY_MASTER.xlsx")
FOCUS = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\focus_fix\focus_live_retest_results.json"
)
REMAINING = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\LINKED_REMAINING_SOURCE_DOWNLOAD_VERIFICATION_2026-08-01.csv"
)
BACKUP = MASTER.with_name(
    f"SOURCE_LINK_INVENTORY_MASTER.bak_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.xlsx"
)

TESTED_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _verdict_to_usable(verdict: str, usable_rows: int) -> str:
    if verdict == "DIRECT_USABLE_POPULATED" and usable_rows > 0:
        return "YES"
    if verdict == "CONDITIONAL_EMPTY":
        return "NO_VALID_EMPTY"
    if verdict == "STALE_FALLBACK_NOT_USABLE":
        return "NO_STALE_FALLBACK"
    if verdict in {"NOT_DIRECT_ALIAS", "ALIAS"}:
        return "NO_ALIAS_ONLY"
    if verdict == "NOT_USABLE":
        return "NO_NOT_PARSED_MARKET_ROWS"
    return "NO"


def _parser_state(item: dict) -> str:
    state = item.get("state") or ""
    parser = item.get("parser_state") or ""
    verdict = item.get("verdict") or ""
    if verdict == "DIRECT_USABLE_POPULATED":
        return f"{state}|USABLE_PARSED_ROWS"
    if verdict == "CONDITIONAL_EMPTY":
        return f"{state}|CONDITIONAL_EMPTY"
    if verdict == "STALE_FALLBACK_NOT_USABLE":
        return f"{state}|NOT_USABLE"
    return f"{state}|{parser or 'NOT_USABLE'}"


def main() -> None:
    focus = json.loads(FOCUS.read_text(encoding="utf-8"))
    remaining = pd.read_csv(REMAINING)

    # Load all sheets
    xl = pd.ExcelFile(MASTER)
    sheets = {name: pd.read_excel(MASTER, sheet_name=name) for name in xl.sheet_names}
    evidence = sheets["DOWNLOAD_TEST_EVIDENCE"].copy()

    # Build updates from focus retest + remaining CSV baseline
    focus_by_key = {item["source_key"]: item for item in focus}

    # Also re-map remaining usable keys as baseline evidence if not overwritten
    for _, row in remaining.iterrows():
        key = str(row["source_key"])
        if key in focus_by_key:
            continue
        # keep existing evidence; only ensure remaining verdicts are known
        pass

    updated_keys: list[str] = []
    for key, item in focus_by_key.items():
        usable_rows = int(item.get("usable_rows") or 0)
        usable = _verdict_to_usable(str(item.get("verdict") or ""), usable_rows)
        parser_state = _parser_state(item)
        sample_fields = item.get("sample_fields")
        sample_row_json = item.get("sample_row_json")
        raw_path = item.get("raw_path")
        url = item.get("url")
        reason = item.get("summary") or item.get("reason") or item.get("error")
        why = {
            "YES": "Parsed structured market/macro rows with real fields from live download.",
            "NO_VALID_EMPTY": "Official endpoint connected; empty payload is valid for current market window (not populated usable data).",
            "NO_STALE_FALLBACK": "Live fetch failed and only stale cache remained; stale fallback does not count.",
            "NO_NOT_PARSED_MARKET_ROWS": "Downloaded payload could not be parsed into market rows (WAF/HTML/access or schema mismatch).",
            "NO_ALIAS_ONLY": "Alias/companion row; not a direct independent data endpoint.",
        }.get(usable, reason)

        mask = evidence["source_key"].astype(str) == key
        payload = {
            "resolved_data_url": url,
            "parser_state": parser_state,
            "usable_for_screener_download": usable,
            "why_counted_or_not": why,
            "usable_rows": usable_rows if usable == "YES" else 0,
            "data_date": item.get("data_date"),
            "sample_fields": sample_fields,
            "sample_row_json": sample_row_json,
            "raw_path_or_archive": raw_path,
            "summary": reason,
            "parsed_at": TESTED_AT,
        }
        if mask.any():
            for col, value in payload.items():
                if col in evidence.columns:
                    evidence.loc[mask, col] = value
            # optional extra columns if present
            for col in ("tested_at", "failure_reason", "next_action"):
                if col in evidence.columns:
                    if col == "tested_at":
                        evidence.loc[mask, col] = TESTED_AT
                    elif col == "failure_reason":
                        evidence.loc[mask, col] = None if usable == "YES" else reason
                    elif col == "next_action":
                        if usable == "YES":
                            evidence.loc[mask, col] = "MONITOR_FRESHNESS_SCHEMA_DRIFT"
                        elif usable == "NO_VALID_EMPTY":
                            evidence.loc[mask, col] = "RETEST_DURING_MARKET_HOURS_OR_EVENT_WINDOW"
                        elif key == "nsdl_fpi_fortnightly":
                            evidence.loc[mask, col] = (
                                "RESOLVE_WAF_OR_USE_COMPANION_LATEST_DAILY_NSDL"
                            )
                        else:
                            evidence.loc[mask, col] = "INVESTIGATE_ACCESS_OR_SCHEMA"
        else:
            new_row = {
                "evidence_group": "FOCUS_FIX_2026_08_01",
                "source_key": key,
                "source_name": key,
                "catalog_url": url,
                **payload,
            }
            # fill missing columns
            for col in evidence.columns:
                new_row.setdefault(col, None)
            evidence = pd.concat([evidence, pd.DataFrame([new_row])], ignore_index=True)
        updated_keys.append(key)

    sheets["DOWNLOAD_TEST_EVIDENCE"] = evidence

    # Update DOWNLOAD_TEST_SUMMARY metrics if sheet exists
    if "DOWNLOAD_TEST_SUMMARY" in sheets:
        summary = sheets["DOWNLOAD_TEST_SUMMARY"].copy()
        yes_count = int((evidence["usable_for_screener_download"] == "YES").sum())
        yes_enriched = int(
            evidence["usable_for_screener_download"]
            .astype(str)
            .str.startswith("YES")
            .sum()
        )
        total_evidence = len(evidence)
        # update known metric rows if present
        metric_updates = {
            "evidence_rows": total_evidence,
            "usable_yes_rows": yes_count,
            "usable_yes_including_enriched": yes_enriched,
            "focus_fix_updated_at": TESTED_AT,
            "focus_fixed_source_keys": ",".join(
                k
                for k, v in focus_by_key.items()
                if v.get("verdict") == "DIRECT_USABLE_POPULATED"
            ),
            "focus_conditional_empty_keys": ",".join(
                k
                for k, v in focus_by_key.items()
                if v.get("verdict") == "CONDITIONAL_EMPTY"
            ),
            "focus_still_failed_keys": ",".join(
                k
                for k, v in focus_by_key.items()
                if v.get("verdict")
                not in {"DIRECT_USABLE_POPULATED", "CONDITIONAL_EMPTY"}
            ),
        }
        if "metric" in summary.columns and "value" in summary.columns:
            for metric, value in metric_updates.items():
                mask = summary["metric"].astype(str) == metric
                if mask.any():
                    summary.loc[mask, "value"] = value
                else:
                    summary = pd.concat(
                        [
                            summary,
                            pd.DataFrame(
                                [
                                    {
                                        "metric": metric,
                                        "value": value,
                                        "meaning": "Updated by focus_source fix retest 2026-08-01",
                                    }
                                ]
                            ),
                        ],
                        ignore_index=True,
                    )
            sheets["DOWNLOAD_TEST_SUMMARY"] = summary

    # Update ALL_LINK_DOWNLOAD_VIEW for matching tested_source_key / active keys
    if "ALL_LINK_DOWNLOAD_VIEW" in sheets:
        view = sheets["ALL_LINK_DOWNLOAD_VIEW"].copy()
        for key, item in focus_by_key.items():
            mask = view.get("tested_source_key", pd.Series(dtype=str)).astype(
                str
            ) == key
            if "active_source_keys" in view.columns:
                mask = mask | view["active_source_keys"].astype(str).str.contains(
                    rf"\b{key}\b", na=False, regex=True
                )
            if not mask.any():
                continue
            usable_rows = int(item.get("usable_rows") or 0)
            usable = _verdict_to_usable(str(item.get("verdict") or ""), usable_rows)
            if "download_usable_rows" in view.columns:
                view.loc[mask, "download_usable_rows"] = (
                    usable_rows if usable == "YES" else 0
                )
            if "download_parser_state" in view.columns:
                view.loc[mask, "download_parser_state"] = _parser_state(item)
            if "download_test_class" in view.columns:
                view.loc[mask, "download_test_class"] = item.get("verdict")
            if "download_evidence_note" in view.columns:
                view.loc[mask, "download_evidence_note"] = item.get("summary") or item.get(
                    "reason"
                )
            if "http_status" in view.columns:
                view.loc[mask, "http_status"] = item.get("status_code")
            if "resolved_url" in view.columns:
                view.loc[mask, "resolved_url"] = item.get("url")
            if "next_action" in view.columns:
                if usable == "YES":
                    view.loc[mask, "next_action"] = "MONITOR_FRESHNESS_SCHEMA_DRIFT"
                elif usable == "NO_VALID_EMPTY":
                    view.loc[mask, "next_action"] = (
                        "RETEST_DURING_MARKET_HOURS_OR_EVENT_WINDOW"
                    )
                else:
                    view.loc[mask, "next_action"] = "INVESTIGATE_ACCESS_OR_SCHEMA"
        sheets["ALL_LINK_DOWNLOAD_VIEW"] = view

    # Backup then write
    BACKUP.write_bytes(MASTER.read_bytes())
    with pd.ExcelWriter(MASTER, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)

    print("backup", BACKUP)
    print("updated keys", updated_keys)
    print(
        "evidence YES count",
        int((evidence["usable_for_screener_download"] == "YES").sum()),
    )
    print(
        "evidence total",
        len(evidence),
    )


if __name__ == "__main__":
    main()
