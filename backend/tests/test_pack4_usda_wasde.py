from __future__ import annotations

import json

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api.parsers.phase2_screener_parsers import parse_usda_wasde_index


XML = b'''<?xml version="1.0"?>
<Report Name="wasde">
  <sr08><Report Name="sr08" Report_Month="July 2026" page_title="WASDE - 673 - 8"
    sub_report_title="World and U.S. Supply and Use for Grains" sub_report_subtitle="Million Metric Tons">
    <matrix1 commodity_header1="World"><groups><commodity commodity1="Total Grains">
      <years><year market_year1="2025/26"><months><month forecast_month1="Jul">
        <attributes><attribute><s3 attribute1="Output"><s4><Cell cell_value1="2858.00" /></s4></s3></attribute></attributes>
      </month></months></year></years>
    </commodity></groups></matrix1>
  </Report></sr08>
</Report>'''


def _bundle() -> bytes:
    return json.dumps(
        {
            "discoveryUrl": "https://esmis.nal.usda.gov/api/v1/release/findByIdentifier/WASDE",
            "release": {
                "id": "795974",
                "release_datetime": "2026-07-10T12:00:00+0000",
                "files": ["https://esmis.nal.usda.gov/release/wasde0726.xml"],
            },
            "xmlUrl": "https://esmis.nal.usda.gov/release/wasde0726.xml",
            "xml": XML.decode(),
        }
    ).encode()


def test_wasde_esmis_bundle_reads_attribute_values_and_release_date() -> None:
    parsed = parse_usda_wasde_index(_bundle(), url="https://esmis.nal.usda.gov/release/wasde0726.xml")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["commodity"] == "Total Grains"
    assert row["marketYear"] == "2025/26"
    assert row["attribute"] == "Output"
    assert row["value"] == 2858.0
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"


def test_wasde_raw_xml_uses_report_month_when_release_metadata_absent() -> None:
    parsed = parse_usda_wasde_index(XML, url="https://www.usda.gov/oce/commodity/wasde/wasde0726.xml")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-01"
    assert parsed["record_count"] == 1


@pytest.mark.parametrize("content", [b"<html>blocked</html>", b"<Report><Cell /></Report>"])
def test_wasde_invalid_or_empty_content_fails_closed(content: bytes) -> None:
    parsed = parse_usda_wasde_index(content)
    assert parsed["record_count"] == 0
    assert parsed["parser_state"] == "WAIT_EMPTY_PARSE"


class _Response:
    def __init__(self, status: int, content: bytes, payload: object | None = None) -> None:
        self.status_code = status
        self.content = content
        self._payload = payload
        self.headers = {"content-type": "application/json"}
        self.encoding = "utf-8"
        self.text = content.decode(errors="replace")

    def json(self) -> object:
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _Session:
    def get(self, url: str, **_kwargs: object) -> _Response:
        if "release/findByIdentifier" in url:
            return _Response(
                200,
                b"{}",
                {"results": [{"id": "795974", "release_datetime": "2026-07-10T12:00:00+0000", "files": ["https://example.test/wasde0726.xml"]}]},
            )
        if url == "https://example.test/wasde0726.xml":
            response = _Response(200, XML)
            response.headers = {"content-type": "application/xml"}
            return response
        raise AssertionError(f"unexpected fallback request: {url}")


def test_fetcher_prefers_esmis_discovery_and_preserves_xml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(phase3_multi_step_fetch, "_session", lambda _headers: _Session())
    result = phase3_multi_step_fetch.fetch_usda_wasde()
    assert result.ok is True
    assert result.media_type == "application/json"
    payload = json.loads(result.content)
    assert payload["release"]["id"] == "795974"
    assert "cell_value1=\"2858.00\"" in payload["xml"]
