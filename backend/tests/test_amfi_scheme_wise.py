from __future__ import annotations

import json
from datetime import datetime, timezone

from trendforge_api import storage
from trendforge_api.amfi_scheme_wise import (
    build_amfi_scheme_bundle,
    parse_amfi_scheme_directory,
)
from trendforge_api.parsers.amfi_portfolio_parser import parse_amfi_portfolio
from trendforge_api.models import SourceParseResult


DIRECTORY = b"""<script>self.__next_f.push([1,"x:{\\"mutualFunds\\":[
{\\"mf_id\\":\\"28\\",\\"mf_name\\":\\"UTI Mutual Fund\\"},
{\\"mf_id\\":\\"22\\",\\"mf_name\\":\\"SBI Mutual Fund\\"}],
\\"quarters\\":[
{\\"QuarterDate\\":\\"2026-04-01T00:00:00+05:30\\",\\"QuarterName\\":\\"Apr-Jun 2026\\"},
{\\"QuarterDate\\":\\"2026-01-01T00:00:00+05:30\\",\\"QuarterName\\":\\"Jan-Mar 2026\\"}]}" ])</script>"""


def _row(mf_id: str, company: str) -> dict[str, object]:
    return {
        "MF_ID": mf_id,
        "Scheme_ID": f"S-{mf_id}",
        "Scheme_Name": "Equity Fund",
        "ISIN": "INE002A01018",
        "Company_Name": company,
        "Security_Type": "EQUITY SHARES",
        "MarketValue": 125.5,
        "MarketValuePercentage": 2.5,
        "QuarterDate": "2026-01-01T00:00:00.000Z",
        "QuarterName": "Jan-Mar 2026",
    }


def test_amfi_directory_extracts_funds_and_quarters():
    directory = parse_amfi_scheme_directory(DIRECTORY)
    assert [item["mfId"] for item in directory.funds] == [22, 28]
    assert [item["quarterName"] for item in directory.quarters] == [
        "Apr-Jun 2026",
        "Jan-Mar 2026",
    ]


def test_amfi_bundle_falls_back_from_empty_newest_quarter():
    calls: list[str] = []

    def fetch(url: str, _timeout: int):
        calls.append(url)
        if "01-Apr-2026" in url:
            return (
                404,
                {"content-type": "application/json"},
                b'{"message":"No data found."}',
            )
        mf_id = "28" if "MF_ID=28" in url else "22"
        body = json.dumps([_row(mf_id, f"COMPANY {mf_id}")]).encode()
        return 200, {"content-type": "application/json"}, body

    bundle, attempts = build_amfi_scheme_bundle(
        DIRECTORY, fetcher=fetch, timeout_seconds=1, max_workers=1
    )
    payload = json.loads(bundle)
    assert payload["quarterName"] == "Jan-Mar 2026"
    assert payload["coverage"]["state"] == "COMPLETE"
    assert payload["coverage"]["successfulFunds"] == 2
    assert payload["coverage"]["totalRows"] == 2
    assert any(item.result_state == "NO_DATA" for item in attempts)


def test_amfi_nil_response_is_valid_no_data():
    def fetch(url: str, _timeout: int):
        if "MF_ID=28" in url:
            return (
                200,
                {"content-type": "application/json"},
                json.dumps([_row("28", "COMPANY 28")]).encode(),
            )
        return 404, {"content-type": "application/json"}, b'{"message":"Nil"}'

    bundle, _ = build_amfi_scheme_bundle(
        DIRECTORY, fetcher=fetch, timeout_seconds=1, max_workers=1
    )
    coverage = json.loads(bundle)["coverage"]
    assert coverage["state"] == "COMPLETE"
    assert coverage["noDataFunds"] == 1
    assert coverage["failedFunds"] == 0


def test_amfi_http_200_no_data_messages_are_valid_empty():
    for message in ("Nil", "No data found."):
        def fetch(url: str, _timeout: int):
            if "MF_ID=28" in url:
                return (
                    200,
                    {"content-type": "application/json"},
                    json.dumps([_row("28", "COMPANY 28")]).encode(),
                )
            return (
                200,
                {"content-type": "application/json"},
                json.dumps({"message": message}).encode(),
            )

        bundle, attempts = build_amfi_scheme_bundle(
            DIRECTORY, fetcher=fetch, timeout_seconds=1, max_workers=1
        )
        coverage = json.loads(bundle)["coverage"]
        assert coverage["state"] == "COMPLETE"
        assert coverage["noDataFunds"] == 1
        assert coverage["failedFunds"] == 0
        assert any(
            attempt.status_code == 200 and attempt.result_state == "NO_DATA"
            for attempt in attempts
        )


def test_amfi_parser_rejects_partial_bundle():
    payload = {
        "datasetKind": "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE",
        "quarterDate": "2026-01-01",
        "quarterName": "Jan-Mar 2026",
        "coverage": {
            "state": "PARTIAL",
            "requestedFunds": 2,
            "successfulFunds": 1,
            "noDataFunds": 0,
            "failedFunds": 1,
            "totalRows": 1,
        },
        "responses": [
            {
                "mfId": 28,
                "mfName": "UTI Mutual Fund",
                "state": "OK",
                "rows": [_row("28", "RELIANCE INDUSTRIES LTD.")],
            }
        ],
    }
    parsed = parse_amfi_portfolio(json.dumps(payload).encode())
    assert parsed["parser_state"] == "WAIT_PARSE_ERROR"
    assert parsed["record_count"] == 0


def test_amfi_quarterly_exposure_has_no_quantity_claim():
    payload = {
        "datasetKind": "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE",
        "quarterDate": "2026-01-01",
        "quarterName": "Jan-Mar 2026",
        "coverage": {
            "state": "COMPLETE",
            "requestedFunds": 1,
            "successfulFunds": 1,
            "noDataFunds": 0,
            "failedFunds": 0,
            "totalRows": 1,
        },
        "responses": [
            {
                "mfId": 28,
                "mfName": "UTI Mutual Fund",
                "state": "OK",
                "rows": [_row("28", "RELIANCE INDUSTRIES LTD.")],
            }
        ],
    }
    parsed = parse_amfi_portfolio(json.dumps(payload).encode())
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-03-31"
    assert parsed["output"]["datasetKind"] == "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE"
    assert parsed["output"]["quantityAvailable"] is False
    assert parsed["output"]["exposures"][0]["marketValue"] == 125.5
    assert "quantity" not in parsed["output"]["exposures"][0]


def test_amfi_quarterly_exposure_is_not_saved_as_monthly_quantity_delta(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "amfi.db")
    payload = {
        "datasetKind": "AMFI_SCHEME_WISE_QUARTERLY_EXPOSURE",
        "quarterDate": "2026-01-01",
        "quarterName": "Jan-Mar 2026",
        "coverage": {
            "state": "COMPLETE",
            "requestedFunds": 1,
            "successfulFunds": 1,
            "noDataFunds": 0,
            "failedFunds": 0,
            "totalRows": 1,
        },
        "responses": [
            {
                "mfId": 28,
                "mfName": "UTI Mutual Fund",
                "state": "OK",
                "rows": [_row("28", "RELIANCE INDUSTRIES LTD.")],
            }
        ],
    }
    parsed = parse_amfi_portfolio(json.dumps(payload).encode())
    saved = storage.save_source_parse_result(
        SourceParseResult(
            sourceKey="amfi_scheme_wise",
            snapshotId=None,
            parserState=parsed["parser_state"],
            dataDate=parsed["data_date"],
            recordCount=parsed["record_count"],
            summary=parsed["summary"],
            output=parsed["output"],
            error=parsed["error"],
            parsedAt=datetime.now(timezone.utc).isoformat(),
        )
    )
    assert saved.parser_state == "PARSED_STRUCTURED"
    conn = storage.connect()
    try:
        assert (
            conn.execute("SELECT COUNT(*) FROM amfi_scheme_exposure_rows").fetchone()[0]
            == 1
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM amfi_scheme_holdings").fetchone()[0] == 0
        )
        assert conn.execute("SELECT COUNT(*) FROM amfi_stock_deltas").fetchone()[0] == 0
    finally:
        conn.close()
