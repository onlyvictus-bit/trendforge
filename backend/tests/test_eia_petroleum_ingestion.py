from __future__ import annotations

from pathlib import Path

from trendforge_api import storage
from trendforge_api.parsers.eia_petroleum_parser import parse_eia_petroleum_stocks
from trendforge_api.source_parser import parse_source_content
from trendforge_api.source_resolver import direct_download_candidates


EIA_TABLE = (
    b'"STUB_1","7/3/26","6/26/26","Difference","Percent Change",'
    b'"7/4/25","Difference","Percent Change"\n'
    b'"Commercial (Excluding SPR)","411.357","408.359","2.998",'
    b'"0.700","426.021","-14.664","-3.400"\n'
    b'"Total Motor Gasoline","212.062","213.966","-1.904",'
    b'"-0.900","229.468","-17.407","-7.600"\n'
    b'"Distillate Fuel Oil","103.619","108.599","-4.980",'
    b'"-4.600","102.797","0.822","0.800"\n'
    b'"STUB_1","STUB_2","7/3/26","6/26/26","Difference"\n'
)


def test_eia_parser_normalizes_required_weekly_petroleum_stock_rows() -> None:
    parsed = parse_eia_petroleum_stocks(EIA_TABLE)

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-03"
    assert parsed["record_count"] == 3
    assert parsed["output"]["crudeInventoryBias"] == "BEARISH_BUILD"
    assert parsed["output"]["rows"][0] == {
        "metricKey": "COMMERCIAL_EXCLUDING_SPR",
        "metricName": "Commercial (Excluding SPR)",
        "observationDate": "2026-07-03",
        "previousWeekDate": "2026-06-26",
        "yearAgoDate": "2025-07-04",
        "currentValue": 411.357,
        "previousWeekValue": 408.359,
        "weeklyChange": 2.998,
        "weeklyPercentChange": 0.7,
        "yearAgoValue": 426.021,
        "yearChange": -14.664,
        "yearPercentChange": -3.4,
        "units": "million_barrels",
    }


def test_eia_parser_fails_closed_when_required_metric_or_date_is_missing() -> None:
    missing_metric = EIA_TABLE.replace(
        b'"Distillate Fuel Oil","103.619","108.599","-4.980",',
        b'"Other Product","103.619","108.599","-4.980",',
    )
    bad_date = EIA_TABLE.replace(b'"7/3/26"', b'"not-a-date"', 1)

    assert parse_eia_petroleum_stocks(missing_metric)["parser_state"] == (
        "WAIT_SCHEMA_MISMATCH"
    )
    assert parse_eia_petroleum_stocks(bad_date)["parser_state"] == (
        "WAIT_SCHEMA_MISMATCH"
    )


def test_eia_direct_candidate_uses_official_weekly_csv() -> None:
    assert direct_download_candidates("eia_weekly_petroleum_stocks") == [
        "https://ir.eia.gov/wpsr/table1.csv"
    ]


def test_eia_rows_are_persisted_as_crude_context(tmp_path: Path) -> None:
    original_db_path = storage.DB_PATH
    storage.DB_PATH = tmp_path / "eia.db"
    try:
        parsed = parse_source_content(
            "eia_weekly_petroleum_stocks",
            EIA_TABLE,
            url="https://ir.eia.gov/wpsr/table1.csv",
        )
        saved = storage.save_source_parse_result(parsed)
        rows = storage.list_source_domain_rows("eia_weekly_petroleum_stocks", limit=10)

        assert saved.parser_state == "PARSED_STRUCTURED"
        assert len(rows) == 3
        commercial = next(
            row for row in rows if row["metric_key"] == "COMMERCIAL_EXCLUDING_SPR"
        )
        assert commercial["source_key"] == "eia_weekly_petroleum_stocks"
        assert commercial["weekly_change"] == 2.998
    finally:
        storage.DB_PATH = original_db_path
