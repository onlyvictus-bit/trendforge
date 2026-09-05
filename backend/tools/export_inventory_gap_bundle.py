from __future__ import annotations

"""Fetch, archive, normalize and export the seven inventory gap feeds.

This is a thin operational entry point over TrendForge's existing monitor and
parser pipeline.  It does not implement a second downloader or data store.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trendforge_api.source_monitor import check_sources
from trendforge_api.source_parser import parse_source
from trendforge_api.storage import PARSER_VERSION_BY_SOURCE


GAP_KEYS = (
    "nse_trade_to_trade",
    "kite_derivatives_contract_master",
    "nse_board_meetings",
    "nse_most_active_futures",
    "nse_most_active_options",
    "nse_ipo_issue_calendar",
    "nse_pr_market_snapshot",
)
EXPORT_KEYS = ("nse_bhavcopy_eod", *GAP_KEYS)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path)


def build_export(result: Any) -> dict[str, Any]:
    output = dict(result.output or {})
    records = output.get("rows") if isinstance(output.get("rows"), list) else []
    return {
        "key": result.source_key,
        "source_url": output.get("url"),
        "data_date": result.data_date,
        "fetched_at": result.parsed_at,
        "content_hash": output.get("contentHash"),
        "parser_version": PARSER_VERSION_BY_SOURCE.get(result.source_key, "unknown"),
        "parser_state": result.parser_state,
        "records_scope": "complete_normalized_records",
        "source_row_count": output.get("sourceRowCount", len(records)),
        "normalized_row_count": output.get("normalizedRowCount", len(records)),
        "row_count": len(records),
        "summary": result.summary,
        "source_trust": (
            "OPEN_SOURCE_UNOFFICIAL"
            if result.source_key == "kite_derivatives_contract_master"
            else "OFFICIAL"
        ),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    if not args.no_fetch:
        summary = check_sources(list(EXPORT_KEYS), timeout_seconds=args.timeout)
        fetch_states = {row.source_key: row.check_state for row in summary.results}
    else:
        fetch_states = {key: "NOT_RUN" for key in EXPORT_KEYS}

    observed_at = datetime.now(timezone.utc).isoformat()
    manifest_rows = []
    failures = []
    for key in EXPORT_KEYS:
        result = parse_source(key, save=True)
        exported = build_export(result)
        records = exported["records"]
        populated = result.parser_state == "PARSED_STRUCTURED" and bool(records)
        output_path = args.output_root / f"{key}.json"
        # A failed or empty run never overwrites the last populated browser export.
        if populated:
            _write_json(output_path, exported)
        else:
            failures.append(key)
        manifest_rows.append(
            {
                "key": key,
                "fetch_state": fetch_states.get(key),
                "parser_state": result.parser_state,
                "data_date": result.data_date,
                "source_row_count": exported["source_row_count"],
                "normalized_row_count": exported["normalized_row_count"],
                "row_count": len(records),
                "output_path": str(output_path) if populated else None,
                "populated": populated,
                "error": result.error,
            }
        )
    manifest = {
        "generated_at": observed_at,
        "source_activation_ready": False,
        "all_gap_feeds_populated": not any(
            row["key"] in GAP_KEYS and not row["populated"] for row in manifest_rows
        ),
        "feeds": manifest_rows,
    }
    _write_json(args.output_root / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
