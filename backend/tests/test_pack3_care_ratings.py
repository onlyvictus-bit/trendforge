from __future__ import annotations

import json

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api.parsers.care_ratings_parser import parse_care_ratings
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import PARSER_MAP, STRUCTURED_PARSERS
from trendforge_api.source_resolver import resolve_and_fetch_source


def _row(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "CompanyID": "aZLDzd4RvYHcKqz4tXn9VQ==",
        "CompanyName": "North Bihar Highway Limited",
        "FileTitle": "North Bihar Highway Limited: Rating reaffirmed",
        "FileType": "PR",
        "FileURL": "202608160802_North_Bihar_Highway_Limited.pdf",
        "PublishedDate": "2026-08-10 00:00:00.000",
    }
    row.update(changes)
    return row


def _payload(*rows: dict[str, object]) -> bytes:
    return json.dumps({"data": list(rows), "message": "success"}).encode()


def test_care_parser_preserves_identity_date_action_and_pdf() -> None:
    parsed = parse_care_ratings(_payload(_row()), last_modified="2026-08-10T12:00:00Z")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["careCompanyId"].endswith("==")
    assert row["companyName"] == "North Bihar Highway Limited"
    assert row["symbol"] is None
    assert row["ratingAction"] == "RATING_REAFFIRMED"
    assert row["rationaleFilename"].endswith(".pdf")
    assert row["rationaleUrl"].startswith("https://www.careratings.com/upload/CompanyFiles/PR/")
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"


@pytest.mark.parametrize(
    ("content", "state"),
    [
        (b"<html>login</html>", "WAIT_SCHEMA_MISMATCH"),
        (_payload(), "WAIT_EMPTY_PARSE"),
        (json.dumps({"data": "bad"}).encode(), "WAIT_SCHEMA_MISMATCH"),
        (_payload(_row(PublishedDate="bad")), "WAIT_SCHEMA_MISMATCH"),
        (_payload(_row(PublishedDate="2026-08-11")), "WAIT_SCHEMA_MISMATCH"),
    ],
)
def test_care_parser_fails_closed(content: bytes, state: str) -> None:
    parsed = parse_care_ratings(content, last_modified="2026-08-10T12:00:00Z")
    assert parsed["parser_state"] == state
    assert parsed["record_count"] == 0


def test_care_dedupes_deterministically_and_never_invents_symbol() -> None:
    content = _payload(_row(), _row(), _row(CompanyID="two", CompanyName="Second"))
    first = parse_care_ratings(content, last_modified="2026-08-10T12:00:00Z")
    second = parse_care_ratings(content, last_modified="2026-08-10T12:00:00Z")
    assert first == second
    assert first["record_count"] == 2
    assert first["output"]["sourceRowCount"] == 3
    assert first["output"]["duplicateRowCount"] == 1
    assert all(row["symbol"] is None for row in first["output"]["rows"])


def test_care_is_registered_and_uses_existing_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert get_source_descriptor("care_ratings") is not None
    assert "care_ratings" in STRUCTURED_PARSERS
    assert "care_ratings" in PARSER_MAP
    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_care_ratings",
        lambda: MultiStepFetchResult(True, "https://www.careratings.com/rrcompany", 200, _payload(_row()), "application/json", None),
    )
    resolved = resolve_and_fetch_source("care_ratings", "https://www.careratings.com/find-ratings")
    assert resolved.resolver_state == "CARE_RATING_RATIONALES_JSON"
    assert resolved.content
