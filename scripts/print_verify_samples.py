import json
from pathlib import Path

d = json.loads(
    Path(
        r"D:\TrendForge\data\raw_sources\verified_downloads\2026-08-01\full105\VERIFY_ALL_105_WITH_SAMPLES.json"
    ).read_text(encoding="utf-8")
)
print("DIRECT", d["direct_count"], "COMPANION", d["companion_count"], "TOTAL", d["total"])
print()
print("=== ALL DIRECT (94) ===")
for r in sorted([x for x in d["rows"] if x["mode"] == "DIRECT"], key=lambda x: x["row_no"]):
    s = (r.get("sample_row") or "NO_SAMPLE_IN_SHEET")[:160]
    print(
        f"{r['row_no']:3d} | {str(r['data_key'])[:34]:34s} | rows={r['usable_rows']:6d} | {s}"
    )
print()
print("=== COMPANION ONLY (11) ===")
for r in sorted([x for x in d["rows"] if x["mode"] == "COMPANION"], key=lambda x: x["row_no"]):
    s = (r.get("sample_row") or "NO_SAMPLE_IN_SHEET")[:140]
    print(
        f"{r['row_no']:3d} | {str(r['source_keys'])[:30]:30s} -> {str(r['data_key'])[:28]:28s} | rows={r['usable_rows']:6d} | {s}"
    )
