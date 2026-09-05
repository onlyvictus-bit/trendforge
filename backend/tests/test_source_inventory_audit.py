from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.source_inventory_audit import (
    AuditFetchResponse,
    audit_saved_inventory,
    canonicalize_inventory_url,
)
from trendforge_api.vyom_resolver import BrowserDiscovery


def _with_temp_storage(tmp_path: Path):
    original_db_path = storage.DB_PATH
    storage.DB_PATH = tmp_path / "inventory-audit.db"
    return original_db_path


def test_inventory_audit_accounts_for_every_row_and_deduplicates_tracking_urls(
    tmp_path: Path,
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    try:
        result = audit_saved_inventory(
            urls=[
                "https://www.nseindia.com/reports/fii-dii?utm_source=test",
                "https://www.nseindia.com/reports/fii-dii",
                "https://www.tradingview.com/script/example",
            ],
            fetch_ids=set(),
            archive_root=tmp_path / "archive",
        )

        assert result["totalRows"] == 3
        assert result["recordedRows"] == 3
        rows = storage.list_source_inventory_audit_rows(run_id=result["runId"])
        assert [row["inventory_id"] for row in rows] == [1, 2, 3]
        assert rows[0]["canonical_url"] == rows[1]["canonical_url"]
        assert rows[1]["duplicate_of_inventory_id"] == 1
        assert rows[1]["disposition"] == "DUPLICATE_REJECT"
        assert rows[2]["disposition"] == "REFERENCE_ONLY"
        assert all(row["can_unlock_ready"] == 0 for row in rows)
    finally:
        storage.DB_PATH = original_db_path


def test_official_tabular_artifact_is_bounded_archived_and_never_self_authorizes(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    try:
        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url",
            lambda _url, _timeout, _max_bytes: AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/csv"},
                content=b"SYMBOL,VALUE\nRELIANCE,1\n",
                truncated=False,
            ),
        )

        result = audit_saved_inventory(
            urls=["https://nsearchives.nseindia.com/content/equities/report.csv"],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]

        assert row["fetch_state"] == "TABULAR_ARTIFACT_CANDIDATE"
        assert row["disposition"] == "BUILD_OR_MAP_PARSER"
        assert row["content_hash"]
        assert Path(row["raw_path"]).read_bytes() == b"SYMBOL,VALUE\nRELIANCE,1\n"
        assert row["can_unlock_ready"] == 0
    finally:
        storage.DB_PATH = original_db_path


def test_antibot_html_is_recorded_as_blocked_not_data(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    try:
        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url",
            lambda _url, _timeout, _max_bytes: AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"<html><title>Just a moment...</title><p>cf-chl-captcha</p></html>",
                truncated=False,
            ),
        )

        result = audit_saved_inventory(
            urls=["https://www.nseindia.com/all-reports-derivatives"],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]

        assert row["fetch_state"] == "ANTI_BOT_RESPONSE"
        assert row["disposition"] == "BLOCKED_ANTI_BOT"
        assert row["raw_path"] is None
    finally:
        storage.DB_PATH = original_db_path


def test_static_html_scraping_follows_same_organization_artifact_links(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    fetched_urls: list[str] = []
    try:

        def fake_fetch(url: str, _timeout: int, _max_bytes: int) -> AuditFetchResponse:
            fetched_urls.append(url)
            if url.endswith("report.csv"):
                return AuditFetchResponse(
                    status_code=200,
                    headers={"content-type": "text/csv"},
                    content=b"SYMBOL,VALUE\nRELIANCE,1\n",
                    truncated=False,
                )
            return AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b'<html><a href="/downloads/report.csv">CSV</a></html>',
                truncated=False,
            )

        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url",
            fake_fetch,
        )

        result = audit_saved_inventory(
            urls=["https://www.nseindia.com/reports/example"],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]
        links = json.loads(row["discovered_urls_json"])

        assert fetched_urls == [
            "https://www.nseindia.com/reports/example",
            "https://www.nseindia.com/downloads/report.csv",
        ]
        assert row["fetch_state"] == "TABULAR_ARTIFACT_CANDIDATE"
        assert row["scraper_state"] == "STATIC_FOLLOWED"
        assert links == ["https://www.nseindia.com/downloads/report.csv"]
        assert row["disposition"] == "BUILD_OR_MAP_PARSER"
        assert Path(row["raw_path"]).read_bytes() == b"SYMBOL,VALUE\nRELIANCE,1\n"
    finally:
        storage.DB_PATH = original_db_path


def test_static_html_does_not_follow_unrelated_or_private_artifact_links(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    fetched_urls: list[str] = []
    try:

        def fake_fetch(url: str, _timeout: int, _max_bytes: int) -> AuditFetchResponse:
            fetched_urls.append(url)
            return AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/html"},
                content=(
                    b'<a href="https://unrelated.example/report.csv">external</a>'
                    b'<a href="http://127.0.0.1/private.csv">private</a>'
                ),
                truncated=False,
            )

        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url", fake_fetch
        )
        result = audit_saved_inventory(
            urls=["https://www.nseindia.com/reports/example"],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]

        assert fetched_urls == ["https://www.nseindia.com/reports/example"]
        assert row["fetch_state"] == "HTML_WITH_ARTIFACT_LINKS"
        assert row["disposition"] == "RESOLVER_REQUIRED"
    finally:
        storage.DB_PATH = original_db_path


def test_static_html_ignores_known_unrelated_global_footer_downloads(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    fetched_urls: list[str] = []
    try:

        def fake_fetch(url: str, _timeout: int, _max_bytes: int) -> AuditFetchResponse:
            fetched_urls.append(url)
            return AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/html"},
                content=(
                    b'<a href="/docs/list-of-fake-trading-apps_entities.xlsx">'
                    b"Unrelated footer file</a>"
                ),
                truncated=False,
            )

        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url", fake_fetch
        )
        result = audit_saved_inventory(
            urls=["https://www.mcxindia.com/market-data/bhav-copy"],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]

        assert fetched_urls == ["https://www.mcxindia.com/market-data/bhav-copy"]
        assert row["fetch_state"] == "HTML_METADATA_ONLY"
    finally:
        storage.DB_PATH = original_db_path


def test_json_payload_is_profiled_into_a_clean_schema_candidate(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    try:
        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url",
            lambda _url, _timeout, _max_bytes: AuditFetchResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                content=b'{"data":[{"symbol":"ABC","value":1},{"symbol":"XYZ","value":2}]}',
                truncated=False,
            ),
        )
        result = audit_saved_inventory(
            urls=["https://www.nseindia.com/api/example"],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]
        profile = json.loads(row["payload_profile_json"])

        assert row["fetch_state"] == "JSON_ARTIFACT_CANDIDATE"
        assert row["normalization_state"] == "SOURCE_SCHEMA_REQUIRED"
        assert profile["format"] == "JSON"
        assert profile["recordCount"] == 2
        assert profile["fieldNames"] == ["symbol", "value"]
    finally:
        storage.DB_PATH = original_db_path


def test_json_profiler_recognizes_exchange_table_envelopes(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    try:
        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url",
            lambda _url, _timeout, _max_bytes: AuditFetchResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                content=b'{"table":[{"scrip_cd":"500001","offer_price":100}]}',
                truncated=False,
            ),
        )
        result = audit_saved_inventory(
            urls=["https://api.bseindia.com/example"],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]
        profile = json.loads(row["payload_profile_json"])

        assert profile["recordCount"] == 1
        assert profile["fieldNames"] == ["offer_price", "scrip_cd"]
    finally:
        storage.DB_PATH = original_db_path


def test_html_table_is_extracted_as_quarantined_structured_candidate(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    try:
        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url",
            lambda _url, _timeout, _max_bytes: AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/html"},
                content=(
                    b"<html><table><tr><th>Symbol</th><th>Value</th></tr>"
                    b"<tr><td>ABC</td><td>1</td></tr></table></html>"
                ),
                truncated=False,
            ),
        )
        result = audit_saved_inventory(
            urls=["https://www.nseindia.com/reports/example-table"],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]
        profile = json.loads(row["payload_profile_json"])

        assert row["fetch_state"] == "HTML_STRUCTURED_CANDIDATE"
        assert row["normalization_state"] == "SOURCE_SCHEMA_REQUIRED"
        assert profile["tableCount"] == 1
        assert profile["tableHeaders"] == ["Symbol", "Value"]
        assert row["can_unlock_ready"] == 0
    finally:
        storage.DB_PATH = original_db_path


def test_browser_scraper_is_optional_and_remains_candidate_discovery_only(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    try:
        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url",
            lambda _url, _timeout, _max_bytes: AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/html"},
                content=b"<html><body>Dynamic downloads</body></html>",
                truncated=False,
            ),
        )
        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.discover_links_with_vyom",
            lambda _url, _timeout: BrowserDiscovery(
                state="DISCOVERED",
                links=(
                    {
                        "url": "https://www.mcxindia.com/downloads/bhavcopy.zip",
                        "text": "Bhavcopy",
                    },
                ),
                error=None,
            ),
        )

        result = audit_saved_inventory(
            urls=["https://www.mcxindia.com/market-data/bhav-copy"],
            fetch_ids={1},
            use_browser=True,
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]

        assert row["fetch_state"] == "HTML_WITH_ARTIFACT_LINKS"
        assert row["scraper_state"] == "BROWSER_DISCOVERED"
        assert row["can_unlock_ready"] == 0
    finally:
        storage.DB_PATH = original_db_path


def test_active_source_mapping_prefers_verified_direct_candidate_over_landing_page(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    landing = "https://www.nseindia.com/market-data/large-deals"
    artifact = "https://archives.nseindia.com/content/equities/bulk.csv"
    fetched_urls: list[str] = []
    try:
        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.direct_download_candidates",
            lambda source_key: [artifact] if source_key == "nse_large_deals" else [],
        )

        def fake_fetch(url: str, _timeout: int, _max_bytes: int) -> AuditFetchResponse:
            fetched_urls.append(url)
            return AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/csv"},
                content=b"SYMBOL,CLIENT,PRICE\nABC,FUND,100\n",
                truncated=False,
            )

        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url", fake_fetch
        )

        result = audit_saved_inventory(
            urls=[landing],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]

        assert fetched_urls == [artifact]
        assert row["resolved_url"] == artifact
        assert json.loads(row["mapped_source_keys_json"]) == ["nse_large_deals"]
        assert row["fetch_state"] == "TABULAR_ARTIFACT_CANDIDATE"
        assert row["disposition"] == "MAP_EXISTING_SOURCE"
        assert Path(row["raw_path"]).suffix == ".csv"
    finally:
        storage.DB_PATH = original_db_path


def test_fred_landing_page_is_resolved_to_official_csv_candidate(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    landing = "https://fred.stlouisfed.org/series/DFII10"
    artifact = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10"
    fetched_urls: list[str] = []
    try:

        def fake_fetch(url: str, _timeout: int, _max_bytes: int) -> AuditFetchResponse:
            fetched_urls.append(url)
            return AuditFetchResponse(
                status_code=200,
                headers={"content-type": "text/csv"},
                content=b"observation_date,DFII10\n2026-07-10,1.75\n",
                truncated=False,
            )

        monkeypatch.setattr(
            "trendforge_api.source_inventory_audit.fetch_inventory_url", fake_fetch
        )
        result = audit_saved_inventory(
            urls=[landing],
            fetch_ids={1},
            archive_root=tmp_path / "archive",
            throttle_seconds=0,
        )
        row = storage.list_source_inventory_audit_rows(run_id=result["runId"])[0]

        assert fetched_urls == [artifact]
        assert row["resolved_url"] == artifact
        assert row["fetch_state"] == "TABULAR_ARTIFACT_CANDIDATE"
        assert row["normalization_state"] == "MAPPED_PARSER_REVIEW"
    finally:
        storage.DB_PATH = original_db_path


def test_tracking_parameter_canonicalization_is_deterministic() -> None:
    assert (
        canonicalize_inventory_url(
            "HTTPS://WWW.NSEINDIA.COM/reports/fii-dii/?b=2&utm_source=x&a=1#part"
        )
        == "https://www.nseindia.com/reports/fii-dii?a=1&b=2"
    )


def test_inventory_audit_api_exposes_complete_dry_run_and_saved_rows(
    tmp_path: Path, monkeypatch
) -> None:
    original_db_path = _with_temp_storage(tmp_path)
    monkeypatch.setattr(
        "trendforge_api.source_inventory_audit.DEFAULT_REPORT_ROOT",
        tmp_path / "reports",
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/source-inventory/audit",
            json={"fetchIds": [], "useBrowser": False},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["totalRows"] == 211
        assert payload["recordedRows"] == 211

        runs = client.get("/api/source-inventory/audit-runs").json()
        rows = client.get(
            "/api/source-inventory/audit-rows",
            params={"runId": payload["runId"], "limit": 500},
        ).json()
        assert runs[0]["run_id"] == payload["runId"]
        assert len(rows) == 211
    finally:
        storage.DB_PATH = original_db_path
