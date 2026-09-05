from __future__ import annotations

import json

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api.parsers.angelone_instrument_master_parser import (
    parse_angelone_instrument_master,
)
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import PARSER_MAP, STRUCTURED_PARSERS
from trendforge_api.source_resolver import resolve_and_fetch_source


def _row(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "token": "35001",
        "symbol": "NIFTY27AUG2625000CE",
        "name": "NIFTY",
        "expiry": "27AUG2026",
        "strike": "2500000.000000",
        "lotsize": "75",
        "instrumenttype": "OPTIDX",
        "exch_seg": "NFO",
        "tick_size": "5.000000",
        "freeze_qty": "1800",
        "is_cas_enabled": False,
    }
    row.update(changes)
    return row


def _payload(*rows: dict[str, object]) -> bytes:
    return json.dumps(list(rows)).encode()


def test_angel_parser_preserves_broker_identity_and_controls() -> None:
    parsed = parse_angelone_instrument_master(
        _payload(_row()), last_modified="2026-08-10T12:00:00Z"
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    row = parsed["output"]["rows"][0]
    assert row["sampleBrokerTokens"] == ["35001"]
    assert row["sampleInstrumentSymbols"][0].endswith("CE")
    assert row["lotSizes"] == [75.0]
    assert row["freezeQuantities"] == [1800.0]
    assert row["symbol"] is None
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"


@pytest.mark.parametrize(
    ("content", "state"),
    [
        (b"<html>blocked</html>", "WAIT_SCHEMA_MISMATCH"),
        (_payload(), "WAIT_EMPTY_PARSE"),
        (json.dumps({"data": []}).encode(), "WAIT_SCHEMA_MISMATCH"),
        (_payload(_row(token="")), "WAIT_SCHEMA_MISMATCH"),
        (_payload(_row(lotsize="0")), "WAIT_SCHEMA_MISMATCH"),
    ],
)
def test_angel_parser_fails_closed(content: bytes, state: str) -> None:
    parsed = parse_angelone_instrument_master(content, last_modified="2026-08-10T12:00:00Z")
    assert parsed["parser_state"] == state
    assert parsed["record_count"] == 0


def test_angel_parser_dedupes_exchange_token_and_is_deterministic() -> None:
    content = _payload(
        _row(),
        _row(),
        _row(token="35002", exch_seg="BFO", name="SENSEX", symbol="SENSEX27AUG26CE"),
    )
    first = parse_angelone_instrument_master(content, last_modified="2026-08-10T12:00:00Z")
    second = parse_angelone_instrument_master(content, last_modified="2026-08-10T12:00:00Z")
    assert first == second
    assert first["record_count"] == 2
    assert first["output"]["duplicateRowCount"] == 1


def test_angel_source_is_registered_and_uses_existing_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert get_source_descriptor("angelone_instrument_master") is not None
    assert "angelone_instrument_master" in STRUCTURED_PARSERS
    assert "angelone_instrument_master" in PARSER_MAP
    body = _payload(_row())
    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_angelone_instrument_master",
        lambda: MultiStepFetchResult(True, "https://margincalculator.angelone.in/master.json", 200, body, "application/json", None),
    )
    resolved = resolve_and_fetch_source(
        "angelone_instrument_master",
        "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json",
    )
    assert resolved.resolver_state == "ANGELONE_PUBLIC_INSTRUMENT_MASTER"
    assert resolved.content == body
