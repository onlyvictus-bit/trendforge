"""
Fill empty catalog card samples from TrendForge collector last-good objects.

Mirrors the Path A sample bake used by generate_json.py / fix_empty_samples.py,
but sources rows from market_data_latest + content-addressed objects after Refresh
(instead of VERIFY CSV raw dumps).

Safety:
  - Only updates rows with empty records_sample (or REGISTRY_MERGED_AWAITING_SAMPLE).
  - Never clears non-empty samples on historical STRONG cards.
  - Writes a timestamped backup of links_105.json first.

Usage:
  python fill_catalog_samples_from_collector.py
  python fill_catalog_samples_from_collector.py --max-rows 250
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TF_ROOT = Path(r"D:\TrendForge")
CATALOG = TF_ROOT / "frontend" / "inventory-workbench" / "links_105.json"
DB_PATH = TF_ROOT / "data" / "trendforge_research.db"
MARKET_ROOT = TF_ROOT / "data" / "market_data"

# Cap matches generate_json display sample for non-engine feeds
DEFAULT_MAX_ROWS = 250

THIRD_PARTY_FII_KEYS = {
    "screener_in_fii_holding_change",
    "tickertape_fii_holding_change_3m",
    "dhan_fii_holding_change",
    "equitymaster_fii_buys_reference",
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def load_latest_map() -> dict[str, dict[str, Any]]:
    if not DB_PATH.is_file():
        return {}
    # The catalog exporter is a read-only consumer. Opening SQLite in explicit
    # read-only mode avoids journal/lock writes when TrendForge is running.
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT latest.source_key, latest.object_path, latest.data_date,
               latest.fetched_at, latest.normalized_row_count,
               latest.content_hash AS normalized_content_hash,
               (
                   SELECT snapshots.raw_path
                   FROM source_snapshots AS snapshots
                   WHERE snapshots.source_key = latest.source_key
                     AND snapshots.raw_path IS NOT NULL
                     AND snapshots.content_length > 0
                   ORDER BY snapshots.id DESC
                   LIMIT 1
               ) AS raw_path,
               (
                   SELECT snapshots.content_hash
                   FROM source_snapshots AS snapshots
                   WHERE snapshots.source_key = latest.source_key
                     AND snapshots.raw_path IS NOT NULL
                     AND snapshots.content_length > 0
                   ORDER BY snapshots.id DESC
                   LIMIT 1
               ) AS raw_content_hash,
               (
                   SELECT snapshots.checked_at
                   FROM source_snapshots AS snapshots
                   WHERE snapshots.source_key = latest.source_key
                     AND snapshots.raw_path IS NOT NULL
                     AND snapshots.content_length > 0
                   ORDER BY snapshots.id DESC
                   LIMIT 1
               ) AS raw_checked_at
        FROM market_data_latest AS latest
        """
    ).fetchall()
    con.close()
    return {str(r["source_key"]): dict(r) for r in rows}


def load_records_from_object(object_path: str, max_rows: int) -> tuple[list[dict], dict[str, Any]]:
    path = Path(object_path)
    if not path.is_file():
        # hash layout sometimes relative
        alt = MARKET_ROOT / "objects" / path.name[:2] / path.name
        path = alt if alt.is_file() else path
    if not path.is_file():
        return [], {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return [], {}
    rows = data.get("records") or []
    if not rows and isinstance(data.get("payload"), dict):
        payload = data["payload"]
        rows = (
            payload.get("records")
            or payload.get("rows")
            or (payload.get("outputs") or [{}])[0].get("records")
            or (payload.get("outputs") or [{}])[0].get("rows")
            or []
        )
    if not isinstance(rows, list):
        return [], data
    out = [_jsonable(r) for r in rows if isinstance(r, dict)][:max_rows]
    return out, data


def primary_key(item: dict[str, Any]) -> str:
    return str(item.get("active_source_keys") or "").split("|")[0].strip()


def parser_metadata(object_meta: dict[str, Any]) -> dict[str, Any]:
    payload = object_meta.get("payload")
    if not isinstance(payload, dict):
        return {}
    outputs = payload.get("outputs")
    if not isinstance(outputs, list):
        return payload
    usable = [output for output in outputs if isinstance(output, dict)]
    if not usable:
        return {}
    combined = dict(usable[0])
    source_counts = [
        output.get("sourceRowCount")
        for output in usable
        if isinstance(output.get("sourceRowCount"), int)
        and not isinstance(output.get("sourceRowCount"), bool)
        and output.get("sourceRowCount") >= 0
    ]
    if len(source_counts) == len(usable):
        combined["sourceRowCount"] = sum(source_counts)
    return combined


def load_alias_map() -> dict[str, list[str]]:
    """Catalog cards often use the normalized family name; last-good uses the job key."""
    aliases: dict[str, list[str]] = {}
    yaml_path = TF_ROOT / "config" / "source_refresh_profiles.yaml"
    if not yaml_path.is_file():
        return aliases
    try:
        import yaml  # type: ignore[import-untyped]
    except Exception:
        return aliases
    try:
        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return aliases
    sources = payload.get("sources") if isinstance(payload, dict) else payload
    if not isinstance(sources, list):
        return aliases
    for item in sources:
        if not isinstance(item, dict):
            continue
        source_key = str(item.get("source_key") or "").strip()
        normalized = str(item.get("normalized_source_key") or source_key).strip()
        if not source_key:
            continue
        aliases.setdefault(source_key, [])
        if source_key not in aliases[source_key]:
            aliases[source_key].append(source_key)
        aliases.setdefault(normalized, [])
        for key in (source_key, normalized):
            if key and key not in aliases[normalized]:
                aliases[normalized].append(key)
            if key and key not in aliases[source_key]:
                aliases[source_key].append(key)
    return aliases


def lookup_latest(
    latest: dict[str, dict[str, Any]],
    source_key: str,
    aliases: dict[str, list[str]],
) -> tuple[str, dict[str, Any] | None]:
    for candidate in [source_key, *aliases.get(source_key, [])]:
        meta = latest.get(candidate)
        if meta and meta.get("object_path"):
            return candidate, meta
    return source_key, None


def needs_fill(item: dict[str, Any]) -> bool:
    # Docstring contract: only empty samples (or merge-awaiting rows) are filled.
    # Never overwrite a non-empty STRONG sample unless --force-existing.
    sample = item.get("records_sample") or []
    return not bool(sample)


def apply_sample(
    item: dict[str, Any],
    *,
    source_key: str,
    sample: list[dict],
    meta: dict[str, Any],
    object_meta: dict[str, Any],
) -> dict[str, Any]:
    fields = sorted({k for r in sample for k in r.keys()})[:40]
    usable_full = int(meta.get("normalized_row_count") or len(sample) or 0)
    parsed_meta = parser_metadata(object_meta)
    source_rows = parsed_meta.get("sourceRowCount")
    if not isinstance(source_rows, int) or isinstance(source_rows, bool) or source_rows < 0:
        source_rows = usable_full
    parser_version = str(parsed_meta.get("parserVersion") or "").strip()
    source_trust = str(
        parsed_meta.get("sourceTrust")
        or next((row.get("sourceTrust") for row in sample if row.get("sourceTrust")), "")
        or item.get("source_trust")
        or ""
    ).strip()
    data_date = meta.get("data_date") or object_meta.get("dataDate") or item.get("data_date") or ""
    item = dict(item)
    item["records_sample"] = sample
    item["sample_fields"] = fields
    item["sample_row"] = sample[0] if sample else {}
    item["usable_rows"] = usable_full if usable_full > 0 else len(sample)
    item["source_row_count"] = source_rows
    item["normalized_row_count"] = item["usable_rows"]
    item["record_count_str"] = str(item["usable_rows"])
    item["status"] = (
        "THIRD_PARTY"
        if source_key in THIRD_PARTY_FII_KEYS
        else "STRONG" if sample else item.get("status") or "COMPANION"
    )
    item["connection_status"] = (
        "CONNECTED_FRESH_STRUCTURED" if sample else "REGISTRY_MERGED_AWAITING_SAMPLE"
    )
    item["freshness_status"] = f"{source_key}:COLLECTOR_LAST_GOOD"
    item["parser_status"] = f"{source_key}:STRUCTURED_OK"
    item["parser_version"] = parser_version or "UNKNOWN"
    item["data_date"] = data_date
    item["fetched_at"] = meta.get("raw_checked_at") or meta.get("fetched_at") or ""
    item["records_scope"] = "collector_last_good_sample"
    item["content_hash"] = (
        meta.get("raw_content_hash")
        or meta.get("normalized_content_hash")
        or object_meta.get("content_hash")
        or ""
    )
    item["raw_path"] = meta.get("raw_path") or meta.get("object_path") or ""
    if source_trust:
        item["source_trust"] = source_trust
        if source_trust == "OPEN_SOURCE_UNOFFICIAL":
            item["source_role"] = "OPEN_SOURCE_UNOFFICIAL"
    if source_key in THIRD_PARTY_FII_KEYS:
        item["source_role"] = "THIRD_PARTY_INFORMATIONAL"
        item["source_trust"] = "THIRD_PARTY_PUBLIC"
        item["screener_integration"] = "INFO_ONLY_ZERO_SCORE"
        item["safe_use"] = (
            "Informational holding-change/reference evidence only; never a "
            "vote or daily FII stock tape."
        )
    item["next_action"] = "NONE" if sample else "REFRESH_COLLECTOR_FOR_SAMPLES"
    item["summary"] = (
        f"Catalog sample filled from collector last-good ({source_key}, "
        f"n={len(sample)} of {item['usable_rows']})."
        if sample
        else item.get("summary")
    )
    # light entity list from symbol field when present
    symbols: list[str] = []
    for r in sample[:50]:
        sym = r.get("symbol") or r.get("Symbol") or r.get("SYMBOL")
        if sym and str(sym) not in symbols:
            symbols.append(str(sym))
    if symbols:
        item["entity_list"] = symbols[:40]
        item["entity_count"] = len(symbols)
    return item


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument(
        "--catalog",
        default=str(CATALOG),
        help="links_105.json to fill (inventory app or TrendForge workbench)",
    )
    parser.add_argument(
        "--only-key",
        action="append",
        default=[],
        help="Optional source_key filter (repeatable)",
    )
    parser.add_argument(
        "--force-existing",
        action="store_true",
        help="Refresh an existing non-empty sample; requires at least one --only-key.",
    )
    args = parser.parse_args()
    only = set(args.only_key or [])
    if args.force_existing and not only:
        parser.error("--force-existing requires at least one --only-key")

    catalog_path = Path(args.catalog)
    inventory = json.loads(catalog_path.read_text(encoding="utf-8"))
    latest = load_latest_map()
    aliases = load_alias_map()

    filled: list[dict[str, Any]] = []
    still_empty: list[dict[str, Any]] = []
    skipped_nonempty = 0

    for idx, item in enumerate(inventory):
        key = primary_key(item)
        if only and key not in only:
            continue
        if not needs_fill(item) and not (args.force_existing and key in only):
            if item.get("records_sample"):
                skipped_nonempty += 1
            continue
        store_key, meta = lookup_latest(latest, key, aliases)
        if not meta or not meta.get("object_path"):
            still_empty.append({"source_key": key, "row_no": item.get("row_no"), "reason": "no_latest"})
            continue
        sample, obj = load_records_from_object(str(meta["object_path"]), args.max_rows)
        if not sample:
            still_empty.append(
                {
                    "source_key": key,
                    "row_no": item.get("row_no"),
                    "reason": "object_empty",
                    "path": meta.get("object_path"),
                }
            )
            continue
        inventory[idx] = apply_sample(
            item, source_key=key, sample=sample, meta=meta, object_meta=obj
        )
        filled.append(
            {
                "source_key": key,
                "row_no": item.get("row_no"),
                "sample_n": len(sample),
                "usable_rows": inventory[idx]["usable_rows"],
                "data_date": inventory[idx].get("data_date"),
            }
        )

    if not filled:
        print(
            json.dumps(
                {
                    "filled": 0,
                    "still_empty": still_empty,
                    "inventory": len(inventory),
                    "skipped_nonempty": skipped_nonempty,
                },
                indent=2,
            )
        )
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = catalog_path.with_name(f"{catalog_path.name}.bak_fill_{stamp}")
    shutil.copy2(catalog_path, backup)
    catalog_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "backup": str(backup),
                "catalog": str(catalog_path),
                "inventory": len(inventory),
                "filled": len(filled),
                "still_empty": still_empty,
                "skipped_nonempty": skipped_nonempty,
                "items": filled,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
