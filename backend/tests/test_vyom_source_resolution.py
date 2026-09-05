from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.source_resolver import (
    BrowserDiscovery,
    resolve_and_fetch_source,
)
from trendforge_api.vyom_resolver import discover_links_with_vyom, parse_vyom_output


def test_vyom_is_disabled_without_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("TRENDFORGE_ENABLE_VYOM_RESOLVER", raising=False)
    monkeypatch.delenv("TRENDFORGE_VYOM_ROOT", raising=False)

    result = discover_links_with_vyom("https://example.com")

    assert result.state == "DISABLED"
    assert result.links == ()
    assert result.can_unlock_ready is False


def test_vyom_output_is_only_a_candidate_link_result() -> None:
    output = (
        'crawler diagnostics\nVYOM_RESULT={"url":"https://example.com/catalog",'
        '"title":"Downloads","markdown":"ignored",'
        '"links":[{"href":"https://example.com/report.csv","text":"CSV"}]}'
    )

    result = parse_vyom_output(output)

    assert result.state == "DISCOVERED"
    assert result.links == ({"url": "https://example.com/report.csv", "text": "CSV"},)
    assert result.can_unlock_ready is False


def test_resolver_refetches_vyom_candidate_with_trendforge_http(monkeypatch) -> None:
    catalog_url = "https://example.com/catalog"
    artifact_url = "https://example.com/report.csv"
    fetched: list[str] = []

    monkeypatch.setattr(
        "trendforge_api.source_resolver.direct_download_candidates",
        lambda _source_key, today=None: [],
    )

    def fake_fetch(url: str, _timeout: int):
        fetched.append(url)
        if url == catalog_url:
            return 200, {"content-type": "text/html"}, b"<html><body></body></html>"
        if url == artifact_url:
            return 200, {"content-type": "text/csv"}, b"SYMBOL,VALUE\nABC,1\n"
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("trendforge_api.source_resolver.fetch_url", fake_fetch)

    result = resolve_and_fetch_source(
        "nse_large_deals",
        catalog_url,
        browser_discoverer=lambda _url, _timeout: BrowserDiscovery(
            state="DISCOVERED",
            links=({"url": artifact_url, "text": "Large deals CSV"},),
            error=None,
            can_unlock_ready=False,
        ),
    )

    assert result.resolver_state == "VYOM_DISCOVERED_DOWNLOAD"
    assert result.url == artifact_url
    assert result.content == b"SYMBOL,VALUE\nABC,1\n"
    assert fetched == [catalog_url, artifact_url]
    assert [attempt.stage for attempt in result.attempts] == [
        "CATALOG_FETCH",
        "VYOM_DISCOVERY",
        "VYOM_CANDIDATE_FETCH",
    ]
    assert result.attempts[1].can_unlock_ready is False


def test_source_fetch_attempt_ledger_preserves_each_url_result(tmp_path) -> None:
    original_db_path = storage.DB_PATH
    storage.DB_PATH = Path(tmp_path) / "attempts.db"
    try:
        storage.save_source_fetch_attempts(
            "nse_large_deals",
            "attempt-group-1",
            [
                {
                    "url": "https://example.com/catalog",
                    "fetcher": "TRENDFORGE_HTTP",
                    "stage": "CATALOG_FETCH",
                    "result_state": "HTML_ONLY",
                    "status_code": 200,
                    "content_type": "text/html",
                    "content_length": 1200,
                    "duration_ms": 25,
                    "error": None,
                    "can_unlock_ready": False,
                },
                {
                    "url": "https://example.com/report.csv",
                    "fetcher": "TRENDFORGE_HTTP",
                    "stage": "VYOM_CANDIDATE_FETCH",
                    "result_state": "DATA_CANDIDATE",
                    "status_code": 200,
                    "content_type": "text/csv",
                    "content_length": 20,
                    "duration_ms": 31,
                    "error": None,
                    "can_unlock_ready": False,
                },
            ],
        )

        rows = storage.list_source_fetch_attempts(
            source_key="nse_large_deals", limit=10
        )

        assert len(rows) == 2
        assert {row["url"] for row in rows} == {
            "https://example.com/catalog",
            "https://example.com/report.csv",
        }
        assert all(row["can_unlock_ready"] == 0 for row in rows)
        assert all(row["attempt_group_id"] == "attempt-group-1" for row in rows)

        response = TestClient(app).get(
            "/api/source-fetch-attempts",
            params={"sourceKey": "nse_large_deals", "limit": 10},
        )
        assert response.status_code == 200
        assert len(response.json()) == 2
    finally:
        storage.DB_PATH = original_db_path
