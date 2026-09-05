from __future__ import annotations

from datetime import date

from trendforge_api.parsers.nse_fo_bhavcopy_parser import parse_nse_fo_bhavcopy
from trendforge_api.parsers.nse_mwpl_parser import (
    parse_nse_fno_ban,
    parse_nse_mwpl,
    parse_nse_mwpl_percentages,
)
from trendforge_api.parsers.source_freshness import is_data_date_fresh
from trendforge_api.source_monitor import get_source_descriptor, source_catalog_records
from trendforge_api.source_resolver import direct_download_candidates


def test_official_fo_ban_file_extracts_only_real_symbols() -> None:
    parsed = parse_nse_fno_ban(
        b"Securities in Ban For Trade Date 13-JUL-2026:\n1,KAYNES\n"
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-13"
    assert parsed["output"]["evidenceCoverage"] == "FNO_BAN_ONLY"
    assert parsed["output"]["symbols"] == ["KAYNES"]
    assert parsed["output"]["rows"][0]["isBanned"] is True
    assert parsed["output"]["rows"][0]["mwplPercent"] is None


def test_full_mwpl_rows_are_explicitly_coverage_qualified() -> None:
    parsed = parse_nse_mwpl_percentages(
        b"Report Date: 2026-07-10\nSymbol,MWPL,Total OI,Percentage\nRELIANCE,1000000,450000,45\n"
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["output"]["evidenceCoverage"] == "FULL_MWPL_PERCENTAGES"


def test_ncl_combineoi_computes_futeq_utilization_and_no_fresh() -> None:
    parsed = parse_nse_mwpl_percentages(
        b"Date, ISIN, Scrip Name, NSE Symbol, MWPL, Open Interest, "
        b"Future Equivalent Open Interest, Limit for Next Day\n"
        b"21-AUG-2026,INE117A01022,ABB INDIA LIMITED,ABB,7946564,4889375,"
        b"2166073.78542166,5383162\n"
        b"21-AUG-2026,INE114A01011,STEEL AUTHORITY OF INDIA,SAIL,216861410,"
        b"250491200,183775709.8216297,No Fresh Positions\n"
    )
    by_symbol = {row["symbol"]: row for row in parsed["output"]["rows"]}
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert by_symbol["ABB"]["utilizationBasis"] == "FUTEQ_OI"
    assert by_symbol["ABB"]["isBanned"] is False
    assert round(by_symbol["ABB"]["mwplPercent"], 1) == 27.3
    assert by_symbol["SAIL"]["isBanned"] is True
    assert by_symbol["SAIL"]["banStatus"] == "BANNED"


def test_fo_parser_keeps_oi_level_when_change_column_comes_first() -> None:
    parsed = parse_nse_fo_bhavcopy(
        b"Report Date: 2026-08-21\n"
        b"TckrSymb,FinInstrmTp,XpryDt,ClsPric,PrvsClsgPric,ChngInOpnIntrst,OpnIntrst\n"
        b"RELIANCE,STF,29-Sep-2026,1400,1390,-5000,210000\n"
    )
    row = parsed["output"]["rows"][0]
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert row["openInterest"] == 210000
    assert row["oiChange"] == -5000


def test_fno_ban_parser_rejects_mwpl_percentage_table() -> None:
    parsed = parse_nse_fno_ban(
        b"Report Date: 2026-07-10\nSymbol,MWPL,Total OI,Percentage\nRELIANCE,1000000,450000,45\n"
    )

    assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parsed["output"]["expectedContract"] == "nse_fno_ban"


def test_mwpl_percentage_parser_rejects_fno_ban_file() -> None:
    parsed = parse_nse_mwpl_percentages(
        b"Securities in Ban For Trade Date 13-JUL-2026:\n1,KAYNES\n"
    )

    assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parsed["output"]["expectedContract"] == "nse_mwpl_percentages"


def test_fo_parser_fails_closed_when_oi_columns_are_missing() -> None:
    parsed = parse_nse_fo_bhavcopy(
        b"Report Date: 2026-07-10\nTicker Symbol,Closing Price,Previous Closing Price\nRELIANCE,1510,1500\n"
    )

    assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert set(parsed["output"]["missingRequiredColumns"]) == {
        "open_interest",
        "oi_change",
    }


def test_fo_parser_requires_verifiable_trade_date() -> None:
    parsed = parse_nse_fo_bhavcopy(
        b"Ticker Symbol,Closing Price,Previous Closing Price,Open Interest,Change in Open Interest\nRELIANCE,1510,1500,100000,5000\n"
    )

    assert parsed["parser_state"] == "WAIT_SOURCE_DATE"


def test_fno_ban_uses_only_reviewed_current_and_dated_archive_families() -> None:
    fno_ban = direct_download_candidates("nse_fno_ban", today=date(2026, 7, 11))
    legacy_alias = direct_download_candidates("nse_mwpl_ban", today=date(2026, 7, 11))
    percentages = direct_download_candidates(
        "nse_mwpl_percentages", today=date(2026, 7, 11)
    )
    mcx = direct_download_candidates("mcx_bhavcopy", today=date(2026, 7, 11))

    assert fno_ban[:2] == [
        "https://nsearchives.nseindia.com/content/fo/fo_secban.csv",
        "https://archives.nseindia.com/content/fo/fo_secban.csv",
    ]
    assert len(fno_ban) == 16
    assert all(
        "/archives/fo/sec_ban/fo_secban_" in url for url in fno_ban[2:]
    )
    assert legacy_alias == fno_ban
    assert percentages[0] == (
        "https://nsearchives.nseindia.com/archives/nsccl/mwpl/combineoi_11072026.zip"
    )
    assert all("/archives/nsccl/mwpl/combineoi_" in url for url in percentages)
    assert mcx == []


def test_cftc_freshness_respects_friday_release_lag() -> None:
    assert is_data_date_fresh("cftc_cot", "2026-06-30", now=date(2026, 7, 9))
    assert not is_data_date_fresh("cftc_cot", "2026-06-30", now=date(2026, 7, 11))
    assert is_data_date_fresh("cftc_cot", "2026-07-07", now=date(2026, 7, 11))


def test_next_session_fno_ban_file_is_fresh_over_weekend() -> None:
    assert is_data_date_fresh("nse_fno_ban", "2026-07-13", now=date(2026, 7, 11))
    assert not is_data_date_fresh("nse_fno_ban", "2026-07-14", now=date(2026, 7, 11))
    assert is_data_date_fresh("nse_mwpl_ban", "2026-07-13", now=date(2026, 7, 11))


def test_legacy_mwpl_alias_is_non_voting_fno_ban_compatibility() -> None:
    catalog_keys = {item.key for item in source_catalog_records()}
    assert "nse_fno_ban" in catalog_keys
    assert "nse_mwpl_percentages" in catalog_keys
    assert "nse_mwpl_ban" not in catalog_keys

    alias = get_source_descriptor("nse_mwpl_ban")
    assert alias is not None
    assert alias.key == "nse_fno_ban"

    parsed = parse_nse_mwpl(
        b"Securities in Ban For Trade Date 13-JUL-2026:\n1,KAYNES\n"
    )
    assert parsed["output"]["compatibilityAlias"] == "nse_mwpl_ban"
    assert parsed["output"]["canonicalSourceKey"] == "nse_fno_ban"
