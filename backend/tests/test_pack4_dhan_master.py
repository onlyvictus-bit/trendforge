from __future__ import annotations

import csv
import io

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api.parsers.dhan_instrument_master_parser import parse_dhan_instrument_master
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import PARSER_MAP, STRUCTURED_PARSERS
from trendforge_api.source_resolver import resolve_and_fetch_source


FIELDS = [
    "EXCH_ID", "SEGMENT", "SECURITY_ID", "ISIN", "INSTRUMENT",
    "UNDERLYING_SYMBOL", "SYMBOL_NAME", "DISPLAY_NAME", "INSTRUMENT_TYPE",
    "LOT_SIZE", "SM_EXPIRY_DATE", "STRIKE_PRICE", "OPTION_TYPE", "TICK_SIZE",
    "ASM_GSM_FLAG", "ASM_GSM_CATEGORY", "MTF_LEVERAGE", "SM_FREEZE_QTY",
]


def _row(**changes: str) -> dict[str, str]:
    row = {
        "EXCH_ID": "NSE", "SEGMENT": "D", "SECURITY_ID": "12345", "ISIN": "NA",
        "INSTRUMENT": "OPTIDX", "UNDERLYING_SYMBOL": "NIFTY", "SYMBOL_NAME": "NIFTY",
        "DISPLAY_NAME": "NIFTY AUG 25000 CE", "INSTRUMENT_TYPE": "OPTIDX",
        "LOT_SIZE": "75", "SM_EXPIRY_DATE": "2026-08-27", "STRIKE_PRICE": "25000",
        "OPTION_TYPE": "CE", "TICK_SIZE": "0.05", "ASM_GSM_FLAG": "N",
        "ASM_GSM_CATEGORY": "NA", "MTF_LEVERAGE": "0", "SM_FREEZE_QTY": "1800",
    }
    row.update(changes)
    return row


def _csv(*rows: dict[str, str]) -> bytes:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def test_dhan_parser_compacts_controls_and_filters_expired_currency() -> None:
    parsed = parse_dhan_instrument_master(
        _csv(
            _row(),
            _row(SECURITY_ID="12346", OPTION_TYPE="PE"),
            _row(SECURITY_ID="old", SM_EXPIRY_DATE="2026-07-01"),
            _row(SECURITY_ID="currency", SEGMENT="C", INSTRUMENT="FUTCUR"),
        ),
        last_modified="2026-08-10T12:00:00Z",
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 1
    assert parsed["output"]["filteredExpiredContractCount"] == 1
    assert parsed["output"]["filteredOutOfScopeCount"] == 1
    row = parsed["output"]["rows"][0]
    assert row["contractCount"] == 2
    assert row["sampleSecurityIds"] == ["12345", "12346"]
    assert row["optionTypes"] == ["CE", "PE"]
    assert row["symbol"] is None
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"


@pytest.mark.parametrize(
    ("content", "state"),
    [
        (b"<html>blocked</html>", "WAIT_SCHEMA_MISMATCH"),
        (_csv(), "WAIT_EMPTY_PARSE"),
        (b"bad,columns\n1,2\n", "WAIT_SCHEMA_MISMATCH"),
        (_csv(_row(SECURITY_ID="")), "WAIT_SCHEMA_MISMATCH"),
    ],
)
def test_dhan_parser_fails_closed(content: bytes, state: str) -> None:
    parsed = parse_dhan_instrument_master(content, last_modified="2026-08-10T12:00:00Z")
    assert parsed["parser_state"] == state
    assert parsed["record_count"] == 0


def test_dhan_parser_is_deterministic_and_dedupes_security_id() -> None:
    content = _csv(_row(), _row(), _row(SECURITY_ID="2", UNDERLYING_SYMBOL="BANKNIFTY"))
    first = parse_dhan_instrument_master(content, last_modified="2026-08-10T12:00:00Z")
    second = parse_dhan_instrument_master(content, last_modified="2026-08-10T12:00:00Z")
    assert first == second
    assert first["record_count"] == 2
    assert first["output"]["duplicateRowCount"] == 1


def test_dhan_source_is_registered_and_uses_existing_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    assert get_source_descriptor("dhan_instrument_master") is not None
    assert "dhan_instrument_master" in STRUCTURED_PARSERS
    assert "dhan_instrument_master" in PARSER_MAP
    body = _csv(_row())
    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_dhan_instrument_master",
        lambda: MultiStepFetchResult(True, "https://images.dhan.co/master.csv", 200, body, "text/csv", None),
    )
    resolved = resolve_and_fetch_source("dhan_instrument_master", "https://images.dhan.co/api-data/api-scrip-master-detailed.csv")
    assert resolved.resolver_state == "DHAN_PUBLIC_INSTRUMENT_MASTER"
    assert resolved.content == body
