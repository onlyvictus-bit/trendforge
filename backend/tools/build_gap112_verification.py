from __future__ import annotations

"""Extend the historical 105-row verification CSV with the seven gap feeds."""

import csv
import json
from pathlib import Path


OLD = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\VERIFY_ALL_105_WITH_SAMPLES.csv"
)
GAP_ROOT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-04\gap112"
)
OUTPUT_ROOT = Path(
    r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-04\full112"
)
CANONICAL = {
    "nse_trade_to_trade": "https://www.nseindia.com/all-reports",
    "kite_derivatives_contract_master": "https://api.kite.trade/instruments",
    "nse_board_meetings": "https://www.nseindia.com/api/corporate-board-meetings?index=equities",
    "nse_most_active_futures": "https://www.nseindia.com/api/snapshot-derivatives-equity?index=futures",
    "nse_most_active_options": "https://www.nseindia.com/api/snapshot-derivatives-equity?index=options",
    "nse_ipo_issue_calendar": "https://www.nseindia.com/api/ipo-current-issue",
    "nse_pr_market_snapshot": "https://www.nseindia.com/all-reports",
}


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    with OLD.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        old_rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    if len(old_rows) != 105:
        raise RuntimeError(f"Expected 105 historical rows, found {len(old_rows)}")

    bhav_path = GAP_ROOT / "nse_bhavcopy_eod.json"
    bhav = json.loads(bhav_path.read_text(encoding="utf-8"))
    bhav_records = bhav.get("records") or []
    if not bhav_records:
        raise RuntimeError("Refreshed nse_bhavcopy_eod export is empty")
    bhav_matches = [
        row for row in old_rows
        if row.get("source_keys") == "nse_bhavcopy_eod"
        or row.get("data_key") == "nse_bhavcopy_eod"
    ]
    if not bhav_matches:
        raise RuntimeError("Expected at least one bhavcopy verification row")
    bhav_sample = bhav_records[0]
    for bhav_row in bhav_matches:
        bhav_row.update(
            {
                "usable_rows": str(bhav["normalized_row_count"]),
                "url": str(bhav.get("source_url") or bhav_row.get("url") or ""),
                "sample_fields": ";".join(bhav_sample.keys()),
                "sample_row": json.dumps(bhav_sample, ensure_ascii=False, separators=(",", ":")),
                "raw_path": str(bhav_path),
                "summary": bhav.get("summary", ""),
            }
        )

    new_rows = []
    coverage = []
    for index, (key, canonical) in enumerate(CANONICAL.items(), start=106):
        path = GAP_ROOT / f"{key}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") or []
        if not records:
            raise RuntimeError(f"{key} is empty")
        sample = records[0]
        new_rows.append(
            {
                "row_no": str(index),
                "mode": "DIRECT",
                "source_keys": key,
                "data_key": key,
                "usable_rows": str(payload["normalized_row_count"]),
                "url": str(payload.get("source_url") or canonical),
                "sample_fields": ";".join(sample.keys()),
                "sample_row": json.dumps(sample, ensure_ascii=False, separators=(",", ":")),
                "raw_path": str(path),
                "summary": payload.get("summary", ""),
                "canonical_url": canonical,
            }
        )
        coverage.append(
            {
                "inventory_row": index,
                "source_key": key,
                "canonical_url": canonical,
                "source_row_count": payload.get("source_row_count"),
                "normalized_row_count": payload.get("normalized_row_count"),
                "data_date": payload.get("data_date"),
                "parser_state": payload.get("parser_state"),
                "records_scope": payload.get("records_scope"),
                "raw_path": str(path),
            }
        )

    csv_path = OUTPUT_ROOT / "VERIFY_ALL_112_WITH_SAMPLES.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(old_rows + new_rows)
    coverage_path = OUTPUT_ROOT / "FULL_112_COVERAGE.json"
    coverage_path.write_text(
        json.dumps(
            {
                "total_inventory_rows": 112,
                "historical_rows_preserved": 105,
                "new_rows": 7,
                "all_new_rows_populated": True,
                "source_activation_ready": False,
                "refreshed_existing": {
                    "source_key": "nse_bhavcopy_eod",
                    "source_row_count": bhav.get("source_row_count"),
                    "normalized_row_count": bhav.get("normalized_row_count"),
                    "data_date": bhav.get("data_date"),
                    "raw_path": str(bhav_path),
                },
                "feeds": coverage,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(csv_path)
    print(coverage_path)


if __name__ == "__main__":
    main()
