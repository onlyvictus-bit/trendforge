from __future__ import annotations

import io

import pandas as pd
import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api.parsers.free_recovery_global_parser import (
    parse_eia_steo_opec_supply,
    parse_opec_production_adjustment,
)
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import PARSER_MAP, STRUCTURED_PARSERS
from trendforge_api.source_resolver import resolve_and_fetch_source


def _eia_workbook() -> bytes:
    rows = [[None] * 6 for _ in range(9)]
    rows[0][1] = "Table 3c. World Petroleum and Other Liquid Fuels Production (million barrels per day)"
    rows[1][1] = "U.S. Energy Information Administration | Short-Term Energy Outlook - July 2026"
    rows[2][0] = "Forecast date:"
    rows[2][2] = 2026
    rows[3][0] = "Wednesday, July 1, 2026"
    rows[3][2:6] = ["Jan", "Feb", "Mar", "Apr"]
    rows[5][0:6] = ["papr_opec", "OPEC total", 28.0, 28.1, 28.2, 28.3]
    rows[6][0:6] = ["papr_opecplus", "OPEC+ total", 40.0, 40.1, 40.2, 40.3]
    rows[7][0:6] = ["papr_opecplus_opec", "OPEC members subject to OPEC+ agreements", 22.0, 22.1, 22.2, 22.3]
    rows[8][0:6] = ["papr_opecplus_other", "OPEC+ other participants total", 18.0, 18.0, 18.0, 18.0]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, header=False, sheet_name="3ctab")
    return output.getvalue()


def test_eia_steo_parser_emits_dated_supply_and_never_quota() -> None:
    parsed = parse_eia_steo_opec_supply(_eia_workbook())

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-07-01"
    assert parsed["record_count"] == 16
    row = parsed["output"]["rows"][0]
    assert row["seriesCode"] == "papr_opec"
    assert row["period"] == "2026-01"
    assert row["millionBarrelsPerDay"] == 28.0
    assert row["isQuota"] is False
    assert parsed["output"]["metric"] == "SUPPLY_PRODUCTION_NOT_QUOTA"


def test_opec_parser_emits_adjustment_event_without_inventing_country_quotas() -> None:
    html = b"""
    <html><h1>Countries adjust production</h1><p>The seven OPEC+ countries,
    namely Saudi Arabia, Russia, Iraq, Kuwait, Kazakhstan, Algeria, and Oman met
    virtually on 7 June 2026.</p><p>The seven participating countries decided to
    implement a production adjustment of 188 thousand barrels per day. This
    adjustment will be implemented in July 2026 as detailed in the table below.</p></html>
    """

    parsed = parse_opec_production_adjustment(
        html, url="https://www.opec.org/pr-detail/604-16-june-2026.html"
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-06-07"
    row = parsed["output"]["rows"][0]
    assert row["adjustmentThousandBarrelsPerDay"] == 188
    assert row["effectiveMonth"] == "2026-07"
    assert row["isQuota"] is False
    assert row["countryRequiredProductionAvailable"] is False
    assert "Saudi Arabia" in row["participatingCountries"]


@pytest.mark.parametrize("key", ["eia_steo_opec_supply", "opec_production_adjustment"])
def test_global_recovery_sources_are_registered_structured_zero_score(key: str) -> None:
    descriptor = get_source_descriptor(key)
    assert descriptor is not None
    assert key in STRUCTURED_PARSERS
    assert key in PARSER_MAP
    assert "score" in descriptor.limitation.casefold()


def test_global_recovery_resolver_uses_existing_fetch_plane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_eia_steo_opec_supply",
        lambda: MultiStepFetchResult(True, "https://eia.test/steo.xlsx", 200, _eia_workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", None),
    )
    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_opec_production_adjustment",
        lambda: MultiStepFetchResult(True, "https://opec.test/release", 200, b"production adjustment of 188 thousand barrels per day implemented in July 2026", "text/html", None),
    )

    eia = resolve_and_fetch_source("eia_steo_opec_supply", "https://eia.test")
    opec = resolve_and_fetch_source("opec_production_adjustment", "https://opec.test")

    assert eia.resolver_state == "EIA_STEO_OPEC_SUPPLY_WORKBOOK"
    assert opec.resolver_state == "OPEC_PRODUCTION_ADJUSTMENT_RELEASE"
    assert eia.content and opec.content
