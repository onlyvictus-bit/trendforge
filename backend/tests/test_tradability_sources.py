from __future__ import annotations

import io
import json
from datetime import date
from types import SimpleNamespace

import pandas as pd

from trendforge_api.parsers.tradability_source_parser import (
    parse_nse_auction_securities,
    parse_nse_price_bands,
)
from trendforge_api.parsers.surveillance_pledge_fpi_parser import parse_nse_esm
from trendforge_api.source_parser import STRUCTURED_PARSERS
from trendforge_api.source_resolver import (
    direct_download_candidates,
    discover_download_links,
)
from trendforge_api.selection.tradability import (
    SourceEvidenceState,
    load_restriction_sources,
)


def test_esm_parser_requires_real_rows_and_effective_dates() -> None:
    payload = [
        {
            "symbol": "ABC",
            "companyName": "ABC Limited",
            "isin": "INE000A01001",
            "esmSurvIndicator": "Stage II",
            "esmTime": "03-Sep-2026",
            "survCode": "ESM - II",
            "survDesc": "Enhanced Surveillance Measure - Stage II",
        }
    ]
    parsed = parse_nse_esm(json.dumps(payload).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 1
    assert parsed["data_date"] == "2026-09-03"
    assert parsed["output"]["rows"][0]["stage"] == "Stage II"

    assert parse_nse_esm(b"{}")["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parse_nse_esm(b"<html>blocked</html>")["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parse_nse_esm(json.dumps([{"symbol": "ABC"}]).encode())["parser_state"] == "WAIT_SCHEMA_MISMATCH"


def test_esm_structural_empty_is_valid_empty_not_failure() -> None:
    parsed = parse_nse_esm(b"[]")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 0
    assert parsed["output"]["validEmpty"] is True


def test_complete_price_band_csv_produces_symbol_classifications() -> None:
    content = (
        "Symbol,Series,Security Name,Band,Remarks\n"
        "ABC,EQ,ABC LIMITED,5,-\n"
        "XYZ,EQ,XYZ LIMITED,No Band,-\n"
    ).encode()
    parsed = parse_nse_price_bands(
        content,
        url="https://nsearchives.nseindia.com/content/equities/sec_list_02092026.csv",
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 2
    assert parsed["data_date"] == "2026-09-02"
    assert parsed["output"]["rows"] == [
        {
            "symbol": "ABC",
            "series": "EQ",
            "company": "ABC LIMITED",
            "bandPercent": 5.0,
            "hasPriceBand": True,
            "remarks": "-",
        },
        {
            "symbol": "XYZ",
            "series": "EQ",
            "company": "XYZ LIMITED",
            "bandPercent": None,
            "hasPriceBand": False,
            "remarks": "-",
        },
    ]


def test_price_band_parser_fails_closed_on_wrong_schema_or_invalid_band() -> None:
    assert parse_nse_price_bands(b"<html>blocked</html>")["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    bad = b"Symbol,Series,Security Name,Band,Remarks\nABC,EQ,ABC LIMITED,unknown,-\n"
    assert parse_nse_price_bands(bad)["parser_state"] == "WAIT_SCHEMA_MISMATCH"


def _auction_workbook(rows: list[list[object]]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, header=False)
    return output.getvalue()


def test_periodic_auction_workbook_supports_populated_and_nil() -> None:
    populated = parse_nse_auction_securities(
        _auction_workbook([["Symbol", "Series"], ["ABC", "BE"]]),
        url="https://nsearchives.nseindia.com/web/mediaattachment/2026-07/illiquid_09072026.xls",
    )
    assert populated["parser_state"] == "PARSED_STRUCTURED"
    assert populated["record_count"] == 1
    assert populated["data_date"] == "2026-07-09"
    assert populated["output"]["rows"][0]["symbol"] == "ABC"

    empty = parse_nse_auction_securities(
        _auction_workbook([["Symbol", "Series"], ["NIL", None]]),
        url="https://nsearchives.nseindia.com/web/mediaattachment/2026-07/illiquid_09072026.xls",
    )
    assert empty["parser_state"] == "PARSED_STRUCTURED"
    assert empty["record_count"] == 0
    assert empty["output"]["validEmpty"] is True


def test_auction_parser_rejects_html_and_unrecognized_workbook() -> None:
    assert parse_nse_auction_securities(b"<html>error</html>")["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    unknown = _auction_workbook([["Something", "Else"], ["ABC", "BE"]])
    assert parse_nse_auction_securities(unknown)["parser_state"] == "WAIT_SCHEMA_MISMATCH"


def test_resolver_candidates_and_link_filter_are_official_and_dated() -> None:
    bands = direct_download_candidates("nse_price_bands", today=date(2026, 9, 3))
    assert bands[0].endswith("sec_list_03092026.csv")
    assert bands[1].endswith("sec_list_02092026.csv")

    page = b'<a href="https://nsearchives.nseindia.com/web/mediaattachment/2026-07/illiquid_09072026.xls">Download list of illiquid securities</a>'
    links = discover_download_links(
        "https://www.nseindia.com/static/regulations/periodic-call-auction-illiquid-securities",
        page,
        "nse_auction_securities",
    )
    assert links == [
        "https://nsearchives.nseindia.com/web/mediaattachment/2026-07/illiquid_09072026.xls"
    ]


def test_all_three_tradability_sources_have_structured_parsers() -> None:
    for key in ("nse_esm", "nse_price_bands", "nse_auction_securities"):
        assert key in STRUCTURED_PARSERS
        assert callable(STRUCTURED_PARSERS[key])


def test_gate_loader_reads_the_canonical_market_data_last_good(monkeypatch, tmp_path) -> None:
    artifact = tmp_path / "price-bands.csv"
    artifact.write_text(
        json.dumps(
            {
                "sourceKey": "nse_price_bands",
                "normalizedSourceKey": "nse_price_bands",
                "parserState": "PARSED_STRUCTURED",
                "dataDate": "2026-09-02",
                "records": [{"symbol": "ABC", "bandPercent": 5.0}],
                "payload": {
                    "outputs": [
                        {
                            "rows": [{"symbol": "ABC", "bandPercent": 5.0}],
                            "validEmpty": False,
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeStore:
        def latest_for(self, source_key):
            assert source_key == "nse_price_bands"
            return SimpleNamespace(
                content_hash="a" * 64,
                source_url=(
                    "https://nsearchives.nseindia.com/content/equities/"
                    "sec_list_02092026.csv"
                ),
                fetched_at=None,
            )

        def object_path_for_hash(self, content_hash):
            assert content_hash == "a" * 64
            return artifact

    monkeypatch.setattr(
        "trendforge_api.selection.cash_a1_staging.default_market_data_store",
        lambda: FakeStore(),
    )
    loaded = load_restriction_sources(("nse_price_bands",), as_of=date(2026, 9, 3))
    assert loaded["nse_price_bands"].evidence_state is SourceEvidenceState.POPULATED
    assert loaded["nse_price_bands"].rows[0]["bandPercent"] == 5.0


def test_gate_loader_does_not_mistake_archive_members_for_valid_empty_rows(
    monkeypatch, tmp_path
) -> None:
    artifact = tmp_path / "auction.json"
    artifact.write_text(
        json.dumps(
            {
                "sourceKey": "nse_auction_securities",
                "normalizedSourceKey": "nse_auction_securities",
                "parserState": "PARSED_STRUCTURED",
                "dataDate": "2026-07-09",
                "records": [{"name": "[Content_Types].xml", "crc32": "abc"}],
                "payload": {
                    "outputs": [
                        {"rows": [], "validEmpty": True, "noDataNow": True}
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeStore:
        def latest_for(self, _source_key):
            return SimpleNamespace(
                content_hash="b" * 64,
                source_url="https://nsearchives.nseindia.com/illiquid_09072026.xls",
            )

        def object_path_for_hash(self, _content_hash):
            return artifact

    monkeypatch.setattr(
        "trendforge_api.selection.cash_a1_staging.default_market_data_store",
        lambda: FakeStore(),
    )
    loaded = load_restriction_sources(
        ("nse_auction_securities",), as_of=date(2026, 9, 3)
    )
    assert loaded["nse_auction_securities"].evidence_state is SourceEvidenceState.VALID_EMPTY
    assert loaded["nse_auction_securities"].rows == ()
