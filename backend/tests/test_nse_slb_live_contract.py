from __future__ import annotations

from datetime import date

from trendforge_api.parsers.nse_slb_parser import parse_nse_slb
from trendforge_api.source_resolver import direct_download_candidates


def test_slb_direct_candidates_use_current_official_open_position_archives() -> None:
    candidates = direct_download_candidates("nse_slb", today=date(2026, 7, 13))

    assert candidates[0] == (
        "https://nsearchives.nseindia.com/archives/slbs/open_pos/"
        "slb_openpos_13072026.csv"
    )
    assert len(candidates) == 7


def test_slb_open_positions_are_aggregated_across_series_per_symbol() -> None:
    content = (
        b"Sr no,Security,Series,Outstanding Quantity at the end of the day\n"
        b"1,ABB,X8,541499\n"
        b"2,ABB,X9,218206\n"
        b"3,RELIANCE,X8,100\n"
    )

    parsed = parse_nse_slb(
        content,
        url=(
            "https://nsearchives.nseindia.com/archives/slbs/open_pos/"
            "slb_openpos_13072026.csv"
        ),
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-13"
    assert parsed["record_count"] == 2
    rows = {row["symbol"]: row for row in parsed["output"]["rows"]}
    assert rows["ABB"]["openPositions"] == 759705
    assert rows["ABB"]["volume"] == 0
    assert rows["ABB"]["seriesCount"] == 2
    assert rows["RELIANCE"]["openPositions"] == 100
