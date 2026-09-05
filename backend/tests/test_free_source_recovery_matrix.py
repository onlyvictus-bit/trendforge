from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs" / "fable" / "evidence" / "FREE_SOURCE_RECOVERY_77_MATRIX_20260811.csv"


def _rows() -> list[dict[str, str]]:
    with MATRIX.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_recovery_matrix_is_exactly_77_unique_routes_across_all_files() -> None:
    rows = _rows()

    assert len(rows) == 77
    assert len({row["route_id"] for row in rows}) == 77
    assert Counter(row["file"] for row in rows) == {
        "1": 8,
        "2": 6,
        "3": 10,
        "4": 11,
        "5": 15,
        "6": 10,
        "7": 17,
    }
    assert all(row["required_output"].strip() for row in rows)
    assert all(row["resolution_owner"].strip() for row in rows)
    assert all(row["evidence_or_gate"].strip() for row in rows)


def test_recovery_matrix_never_calls_unverified_routes_populated() -> None:
    rows = _rows()
    token_rows = [row for row in rows if "TOKEN_REQUIRED" in row["state"]]
    accumulating = [row for row in rows if row["state"] == "DERIVED_ACCUMULATING"]

    assert len(token_rows) == 8
    assert all("upstox" in row["resolution_owner"].lower() for row in token_rows)
    assert {
        row["route_id"]
        for row in rows
        if row["state"] == "CALCULATED_OUTPUT_POPULATED"
    } == {"F6-07", "F6-09", "F7-04", "F7-05", "F7-08", "F7-13"}
    assert {
        row["route_id"]
        for row in rows
        if row["state"] == "WAIT_DETAILED_XBRL_FACTS"
    } == {"F5-10", "F6-01", "F6-02", "F7-01", "F7-02"}
    assert {row["route_id"] for row in accumulating} == {"F7-15"}
    assert all(row["state"] != "FAILED" for row in rows)
