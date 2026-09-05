from __future__ import annotations

from pathlib import Path

from trendforge_api import storage
from trendforge_api.parsers.fred_series_parser import (
    parse_fred_broad_dollar,
    parse_fred_real_yield,
)
from trendforge_api.source_parser import parse_source_content
from trendforge_api.source_resolver import direct_download_candidates


FRED_REAL_YIELD = (
    b"observation_date,DFII10\n2026-07-08,1.72\n2026-07-09,.\n2026-07-10,1.75\n"
)


def test_fred_parser_normalizes_dates_values_and_explicit_missing_observations() -> (
    None
):
    parsed = parse_fred_real_yield(FRED_REAL_YIELD)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-10"
    assert parsed["record_count"] == 2
    assert parsed["output"]["missingObservationCount"] == 1
    assert parsed["output"]["rows"][-1] == {
        "seriesId": "DFII10",
        "observationDate": "2026-07-10",
        "value": 1.75,
        "units": "percent",
    }


def test_fred_parser_fails_closed_on_wrong_series_or_bad_numeric_value() -> None:
    wrong_series = parse_fred_real_yield(
        b"observation_date,DTWEXBGS\n2026-07-10,120.1\n"
    )
    bad_value = parse_fred_broad_dollar(
        b"observation_date,DTWEXBGS\n2026-07-10,not-a-number\n"
    )

    assert wrong_series["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert bad_value["parser_state"] == "WAIT_SCHEMA_MISMATCH"


def test_fred_direct_candidates_use_official_csv_downloads() -> None:
    assert direct_download_candidates("fred_real_yield_10y") == [
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10"
    ]
    assert direct_download_candidates("fred_broad_dollar_index") == [
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS"
    ]


def test_fred_structured_rows_are_persisted_for_research_context(
    tmp_path: Path,
) -> None:
    original_db_path = storage.DB_PATH
    storage.DB_PATH = tmp_path / "fred.db"
    try:
        parsed = parse_source_content(
            "fred_real_yield_10y",
            FRED_REAL_YIELD,
            url="https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10",
        )
        saved = storage.save_source_parse_result(parsed)
        rows = storage.list_source_domain_rows("fred_real_yield_10y", limit=10)
        freshness = {
            row["source_key"]: row for row in storage.list_source_freshness_status()
        }

        assert saved.parser_state == "PARSED_STRUCTURED"
        assert len(rows) == 2
        assert rows[0]["source_key"] == "fred_real_yield_10y"
        assert rows[0]["series_id"] == "DFII10"
        assert rows[0]["observation_date"] == "2026-07-10"
        assert rows[0]["value"] == 1.75
        assert freshness["fred_real_yield_10y"]["expected_frequency"] == "daily"
    finally:
        storage.DB_PATH = original_db_path
