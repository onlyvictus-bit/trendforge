from __future__ import annotations

import json

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api import source_parser as source_parser_module
from trendforge_api.models import SourceSnapshotRecord
from trendforge_api.parsers.crisil_ratings_parser import parse_crisil_ratings
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import PARSER_MAP, STRUCTURED_PARSERS, parse_source_content
from trendforge_api.source_resolver import resolve_and_fetch_source


def _payload(*docs: dict[str, object]) -> bytes:
    return json.dumps({"numFound": len(docs), "docs": list(docs)}).encode("utf-8")


def _doc(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "companyCode": "WYSTP",
        "companyName": "Wysetek Systems Technologists Private Limited",
        "industryName": "Information Technology",
        "ratingDate": "Aug 10, 2026",
        "transDate": "Aug 10, 2026",
        "heading": "Rating outlook revised to 'Stable'; Ratings Reaffirmed",
        "ratingFileName": "WysetekSystemsTechnologistsPrivateLimited_August 10_ 2026_RR_398130.html",
        "prId": 2194367,
    }
    row.update(overrides)
    return row


def test_crisil_parser_preserves_identity_action_dates_and_lineage() -> None:
    parsed = parse_crisil_ratings(
        _payload(_doc()),
        url="https://www.crisilratings.com/example.results.json",
        last_modified="2026-08-10T12:00:00+00:00",
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 1
    assert parsed["output"]["sourceRowCount"] == 1
    assert parsed["output"]["normalizedRowCount"] == 1
    row = parsed["output"]["rows"][0]
    assert row["crisilCompanyCode"] == "WYSTP"
    assert row["companyName"].startswith("Wysetek")
    assert row["symbol"] is None
    assert row["ratingAction"] == "RATING_REAFFIRMED_OUTLOOK_REVISED"
    assert row["ratingDate"] == "2026-08-10"
    assert row["transactionDate"] == "2026-08-10"
    assert row["rationaleFilename"].endswith(".html")
    assert row["rationaleUrl"].startswith("https://www.crisilratings.com/")
    assert row["sourceTrust"] == "OFFICIAL"
    assert row["scope"] == "STOCK_LEVEL_INFORMATIONAL"
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"
    assert parsed["output"]["unmappedCompanyCount"] == 1


@pytest.mark.parametrize(
    ("content", "state"),
    [
        (_payload(), "WAIT_EMPTY_PARSE"),
        (json.dumps({"docs": "not-a-list"}).encode(), "WAIT_SCHEMA_MISMATCH"),
        (b"<html><body>login shell</body></html>", "WAIT_SCHEMA_MISMATCH"),
        (_payload(_doc(ratingDate="bad", transDate="")), "WAIT_SCHEMA_MISMATCH"),
        (
            _payload(_doc(ratingDate="Aug 11, 2026", transDate="Aug 11, 2026")),
            "WAIT_SCHEMA_MISMATCH",
        ),
    ],
)
def test_crisil_parser_fails_closed_for_unusable_payloads(
    content: bytes, state: str
) -> None:
    parsed = parse_crisil_ratings(
        content, last_modified="2026-08-10T12:00:00+00:00"
    )

    assert parsed["parser_state"] == state
    assert parsed["record_count"] == 0


def test_crisil_parser_deduplicates_deterministically_without_fuzzy_symbol() -> None:
    content = _payload(_doc(), _doc(), _doc(companyCode="TELIP", companyName="Teli Electricals"))

    first = parse_crisil_ratings(content, last_modified="2026-08-10T12:00:00+00:00")
    second = parse_crisil_ratings(content, last_modified="2026-08-10T12:00:00+00:00")

    assert first == second
    assert first["record_count"] == 2
    assert first["output"]["sourceRowCount"] == 3
    assert first["output"]["duplicateRowCount"] == 1
    assert all(row["symbol"] is None for row in first["output"]["rows"])


def test_crisil_is_catalogued_structured_and_zero_score() -> None:
    descriptor = get_source_descriptor("crisil_ratings")

    assert descriptor is not None
    assert descriptor.authority.value == "OFFICIAL"
    assert "crisil_ratings" in STRUCTURED_PARSERS
    assert "crisil_ratings" in PARSER_MAP
    assert "score" in descriptor.limitation.casefold()
    parsed = parse_source_content(
        "crisil_ratings",
        _payload(_doc()),
        url=descriptor.url,
        last_modified="2026-08-10T12:00:00+00:00",
    )
    assert parsed.parser_state == "PARSED_STRUCTURED"
    assert parsed.record_count == 1


def test_crisil_resolver_uses_existing_multistep_plane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch() -> MultiStepFetchResult:
        return MultiStepFetchResult(
            True,
            "https://www.crisilratings.com/example.results.json",
            200,
            _payload(_doc()),
            "application/json",
            None,
        )

    monkeypatch.setattr(phase3_multi_step_fetch, "fetch_crisil_ratings", fake_fetch)
    descriptor = get_source_descriptor("crisil_ratings")
    assert descriptor is not None

    resolved = resolve_and_fetch_source("crisil_ratings", descriptor.url)

    assert resolved.status_code == 200
    assert resolved.resolver_state == "CRISIL_RATING_RATIONALES_JSON"
    assert json.loads(resolved.content)["docs"]


def test_crisil_failed_refresh_retains_last_populated_raw_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = _payload(_doc())
    descriptor = get_source_descriptor("crisil_ratings")
    assert descriptor is not None
    broken = SourceSnapshotRecord(
        id=2,
        sourceKey="crisil_ratings",
        name=descriptor.name,
        url=descriptor.url,
        checkState="BROKEN",
        error="simulated fetch failure",
        checkedAt="2026-08-10T15:30:00+00:00",
        changed=False,
    )
    populated = SourceSnapshotRecord(
        id=1,
        sourceKey="crisil_ratings",
        name=descriptor.name,
        url=descriptor.url,
        checkState="NEW",
        statusCode=200,
        contentHash="abc",
        contentLength=len(content),
        rawPath="ignored.json",
        checkedAt="2026-08-10T15:00:00+00:00",
        changed=True,
    )
    monkeypatch.setattr(source_parser_module, "get_latest_source_snapshot", lambda _key: broken)
    monkeypatch.setattr(
        source_parser_module, "get_latest_populated_source_snapshot", lambda _key: populated
    )
    monkeypatch.setattr(source_parser_module, "read_snapshot_bytes", lambda _path: content)

    parsed = source_parser_module.structured_parse("crisil_ratings")

    assert parsed.parser_state == "PARSED_STRUCTURED"
    assert parsed.record_count == 1
    assert parsed.snapshot_id == 1
    assert parsed.output["latestFetchState"] == "BROKEN"
    assert parsed.output["retainedSnapshotAfterFetchFailure"] is True
