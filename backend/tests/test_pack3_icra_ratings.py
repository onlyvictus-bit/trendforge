from __future__ import annotations

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api.parsers.icra_ratings_parser import parse_icra_ratings
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import PARSER_MAP, STRUCTURED_PARSERS
from trendforge_api.source_resolver import resolve_and_fetch_source


ROW = """
<table><tr><th>Date</th><th>Sector</th><th>Reports</th><th></th><th>Action</th></tr>
<tr><td>10 Aug 2026</td><td>Corporate Debt Rating</td><td>
<a href="/Rationale/ShowRationaleReport?Id=144873">Aquatica Frozen Foods Global Private Limited: Ratings upgraded and assigned for enhanced amount</a></td>
<td><a href="/Rating/BankFacilities?CompanyId=27636&amp;CompanyName=Aquatica">Lender-wise facilities</a></td>
<td><a href="/Rating/GetRationalReportFilePdf?Id=144873">PDF</a></td></tr></table>
"""


def test_icra_parser_preserves_company_action_dates_and_links() -> None:
    parsed = parse_icra_ratings(ROW.encode(), last_modified="2026-08-10T12:00:00Z")
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["companyName"].startswith("Aquatica")
    assert row["symbol"] is None
    assert row["ratingAction"] == "RATING_UPGRADED_AND_ASSIGNED"
    assert row["rationaleUrl"].startswith("https://www.icra.in/Rationale/")
    assert row["facilityUrl"].startswith("https://www.icra.in/Rating/BankFacilities")
    assert row["pdfUrl"].endswith("Id=144873")
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"


@pytest.mark.parametrize(
    ("content", "state"),
    [
        (b"<html>login shell</html>", "WAIT_SCHEMA_MISMATCH"),
        (b"<table><tr><th>Date</th><th>Sector</th></tr></table>", "WAIT_EMPTY_PARSE"),
        (ROW.replace("10 Aug 2026", "bad date").encode(), "WAIT_SCHEMA_MISMATCH"),
        (ROW.replace("10 Aug 2026", "11 Aug 2026").encode(), "WAIT_SCHEMA_MISMATCH"),
    ],
)
def test_icra_parser_fails_closed(content: bytes, state: str) -> None:
    parsed = parse_icra_ratings(content, last_modified="2026-08-10T12:00:00Z")
    assert parsed["parser_state"] == state
    assert parsed["record_count"] == 0


def test_icra_is_registered_and_resolver_uses_existing_plane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert get_source_descriptor("icra_ratings") is not None
    assert "icra_ratings" in STRUCTURED_PARSERS
    assert "icra_ratings" in PARSER_MAP
    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_icra_ratings",
        lambda: MultiStepFetchResult(True, "https://www.icra.in/x", 200, ROW.encode(), "text/html", None),
    )
    resolved = resolve_and_fetch_source("icra_ratings", "https://www.icra.in/Rating/AllRatingRationales")
    assert resolved.resolver_state == "ICRA_RATING_RATIONALES_CSRF_HTML"
    assert resolved.content
