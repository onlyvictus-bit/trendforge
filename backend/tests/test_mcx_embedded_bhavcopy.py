from __future__ import annotations

from trendforge_api.parsers.mcx_bhavcopy_parser import parse_mcx_bhavcopy
from trendforge_api.phase3_multi_step_fetch import (
    MultiStepFetchResult,
    fetch_mcx_bhavcopy_page,
)
from trendforge_api.source_resolver import resolve_and_fetch_source
from trendforge_api.source_monitor import source_catalog_records


def test_mcx_embedded_bhavcopy_extracts_futures_without_option_collisions() -> None:
    content = b"""
    <html><body>
      <div id="bhavcopy-data" style="display:none;">[
        {"Date":"07/10/2026","Symbol":"GOLD   ","ExpiryDate":"05AUG2026",
         "Open":144890.0,"High":145061.0,"Low":143324.0,"Close":143478.0,
         "PreviousClose":145300.0,"Volume":4766,"Value":687045.1,
         "OpenInterest":9968,"InstrumentName":"FUTCOM","StrikePrice":0.0,
         "OptionType":"-"},
        {"Date":"07/10/2026","Symbol":"GOLD   ","ExpiryDate":"29JUL2026",
         "Close":106.0,"Volume":977,"OpenInterest":890,
         "InstrumentName":"OPTFUT","StrikePrice":160000.0,"OptionType":"CE"}
      ]</div>
    </body></html>
    """

    parsed = parse_mcx_bhavcopy(
        content, url="https://www.mcxindia.com/market-data/bhav-copy"
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row == {
        "symbol": "GOLD",
        "expiry": "05AUG2026",
        "instrument": "FUTCOM",
        "open": 144890.0,
        "high": 145061.0,
        "low": 143324.0,
        "close": 143478.0,
        "previousClose": 145300.0,
        "volume": 4766,
        "value": 687045.1,
        "openInterest": 9968,
        "oiChange": 0,
        "scope": "MCX_FUTURES_EOD_CONFIRMATION",
    }
    assert parsed["output"]["excludedOptionRows"] == 1


def test_mcx_embedded_bhavcopy_fails_closed_on_invalid_json() -> None:
    parsed = parse_mcx_bhavcopy(
        b'<div id="bhavcopy-data">[{not-json}]</div>',
        url="https://www.mcxindia.com/market-data/bhav-copy",
    )

    assert parsed["parser_state"] == "WAIT_SCHEMA_MISMATCH"
    assert parsed["record_count"] == 0


def test_mcx_catalog_describes_only_the_verified_eod_futures_scope() -> None:
    catalog = {row.key: row for row in source_catalog_records()}

    assert (
        "EMBEDDED_FUTURES_ARTIFACT_LIVE_VERIFIED_2026_07_13"
        in catalog["mcx_bhavcopy"].parser_status
    )
    assert "options" in catalog["mcx_bhavcopy"].limitation.lower()


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int,
        content: bytes,
        url: str,
        content_type: str = "text/html",
    ) -> None:
        self.status_code = status_code
        self.content = content
        self.url = url
        self.headers = {"content-type": content_type}


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []

    def get(self, url: str, **_: object) -> _FakeResponse:
        self.urls.append(url)
        return self.responses.pop(0)


def test_mcx_browser_tls_fetch_accepts_only_populated_embedded_page() -> None:
    content = b'<div id="bhavcopy-data">[{"Date":"08/14/2026"}]</div>'
    session = _FakeSession(
        [
            _FakeResponse(
                status_code=200,
                content=content,
                url="https://www.mcxindia.com/market-data/bhavcopy",
            )
        ]
    )

    result = fetch_mcx_bhavcopy_page(session=session)

    assert result.ok is True
    assert result.content == content
    assert result.url.endswith("/market-data/bhavcopy")


def test_mcx_browser_tls_fetch_rejects_sitefinity_status_page() -> None:
    status_page = (
        b'<html><title>Sitefinity</title><body>ReturnUrl=/market-data/bhavcopy</body></html>'
    )
    session = _FakeSession(
        [
            _FakeResponse(status_code=200, content=status_page, url="https://www.mcxindia.com/sitefinity/status"),
            _FakeResponse(status_code=403, content=b"Access Denied", url="https://www.mcxindia.com/market-data/BhavCopy"),
            _FakeResponse(status_code=404, content=b"Not Found", url="https://www.mcxindia.com/market-data/bhav-copy"),
        ]
    )

    result = fetch_mcx_bhavcopy_page(session=session)

    assert result.ok is False
    assert result.content == b""
    assert "embedded bhavcopy data" in (result.error or "").lower()


def test_mcx_resolver_uses_browser_tls_fetcher(monkeypatch) -> None:
    from trendforge_api import phase3_multi_step_fetch

    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_mcx_bhavcopy_page",
        lambda: MultiStepFetchResult(
            True,
            "https://www.mcxindia.com/market-data/bhavcopy",
            200,
            b'<div id="bhavcopy-data">[{"Date":"08/14/2026"}]</div>',
            "text/html",
            None,
        ),
    )

    resolved = resolve_and_fetch_source(
        "mcx_bhavcopy", "https://www.mcxindia.com/market-data/bhavcopy"
    )

    assert resolved.status_code == 200
    assert resolved.resolver_state == "MCX_BHAVCOPY_CHROME_TLS"
    assert b"bhavcopy-data" in resolved.content
