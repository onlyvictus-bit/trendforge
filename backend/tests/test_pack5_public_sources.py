from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from trendforge_api import phase3_multi_step_fetch
from trendforge_api.parsers.pack5_public_sources_parser import (
    parse_nse_market_status,
    parse_rupeevest_mf_flows,
)
from trendforge_api.phase3_multi_step_fetch import MultiStepFetchResult
from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.market_data_service import (
    MarketDataService,
    ParameterContext,
    RawAcquisition,
    default_normalizer,
)
from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.source_monitor import get_source_descriptor
from trendforge_api.source_parser import PARSER_MAP, STRUCTURED_PARSERS
from trendforge_api.source_resolver import resolve_and_fetch_source


def _market_payload() -> bytes:
    return json.dumps(
        {
            "marketState": [
                {
                    "market": "Capital Market",
                    "marketStatus": "Closed",
                    "tradeDate": "10-Aug-2026 15:30",
                    "index": "NIFTY 50",
                    "last": "24774.30",
                    "variation": "390.70",
                    "percentChange": "1.60",
                    "marketStatusMessage": "Normal Market has Closed",
                },
                {
                    "index": "NIFTY 50",
                    "last": 24774.30,
                    "change": 390.70,
                    "percentChange": 1.60,
                    "timestamp": "10-Aug-2026 15:30",
                },
            ]
        }
    ).encode()


def _rupeevest_payload() -> bytes:
    return json.dumps(
        {
            "search": {
                "stock_data_search": [
                    {
                        "compname": "ABB India Ltd.",
                        "fincode": 100002,
                        "stock_search": "ABB India Ltd. | 500002 | ABB",
                    }
                ]
            },
            "buys": {
                "stock_compare_data": [
                    {
                        "fincode": 100002,
                        "rv_sect_name": "Capital Goods",
                        "compname": "ABB India Ltd.",
                        "classification": "L",
                        "no_of_share_change": 410768,
                        "price_of_share_change": "2933697072.269",
                        "day": "2026-06-30",
                    }
                ]
            },
            "sells": {"stock_compare_data_1": []},
        }
    ).encode()


def test_nse_market_status_parser_is_operational_and_zero_score() -> None:
    parsed = parse_nse_market_status(
        _market_payload(),
        url="https://www.nseindia.com/api/marketStatus",
        last_modified="2026-08-10T16:00:00Z",
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-08-10"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["marketStatus"] == "CLOSED"
    assert row["scoreAuthority"] == "ZERO_SCORE_OPERATIONAL"
    assert parsed["output"]["sourceRowCount"] == 2
    assert parsed["output"]["invalidRowCount"] == 1


def test_nse_market_status_fetch_accepts_auxiliary_index_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        status_code = 200
        url = "https://www.nseindia.com/api/marketStatus"
        content = _market_payload()
        headers = {"content-type": "application/json"}

        @staticmethod
        def json():
            return json.loads(Response.content)

    class Session:
        def get(self, url: str, **_kwargs):
            return Response()

    monkeypatch.setattr(phase3_multi_step_fetch, "_session", lambda *_args, **_kwargs: Session())
    fetched = phase3_multi_step_fetch.fetch_nse_market_status()

    assert fetched.ok is True
    assert fetched.status_code == 200
    assert fetched.content == _market_payload()


def test_market_status_normalizer_preserves_raw_and_normalized_counts() -> None:
    fetched_at = datetime(2026, 8, 10, 16, tzinfo=timezone.utc)
    raw = RawAcquisition.success(
        source_url="https://www.nseindia.com/api/marketStatus",
        status_code=200,
        media_type="application/json",
        content=_market_payload(),
        payload=None,
        fetched_at=fetched_at,
    )
    contract = load_market_data_registry().by_key["nse_market_status"]
    normalized = default_normalizer(
        contract,
        (raw,),
        ParameterContext(
            trading_date=date(2026, 8, 10),
            market_session="CLOSED",
            now=fetched_at,
        ),
    )

    assert normalized.source_row_count == 2
    assert len(normalized.records) == 1


def test_market_status_dedupes_and_rejects_future_or_missing_dates() -> None:
    payload = json.loads(_market_payload())
    valid = dict(payload["marketState"][0])
    payload["marketState"] = [
        valid,
        dict(valid),
        {**valid, "market": "Future", "tradeDate": "11-Aug-2026"},
        {**valid, "market": "Missing date", "tradeDate": ""},
    ]

    parsed = parse_nse_market_status(
        json.dumps(payload).encode(), last_modified="2026-08-10T16:00:00Z"
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 1
    assert parsed["output"]["duplicateRowCount"] == 1
    assert parsed["output"]["invalidRowCount"] == 2


def test_rupeevest_parser_joins_explicit_symbol_and_preserves_signed_flow() -> None:
    parsed = parse_rupeevest_mf_flows(
        _rupeevest_payload(),
        url="https://www.rupeevest.com/Mutual-Fund-Holdings",
        last_modified="2026-08-10T16:00:00Z",
    )
    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["data_date"] == "2026-06-30"
    assert parsed["record_count"] == 1
    row = parsed["output"]["rows"][0]
    assert row["symbol"] == "ABB"
    assert row["direction"] == "BUY"
    assert row["netShareChange"] == 410768
    assert row["approximateValueCr"] == pytest.approx(293.3697)
    assert row["scoreAuthority"] == "ZERO_SCORE_INFORMATIONAL"


def test_rupeevest_dedupes_and_quarantines_unmapped_or_future_rows() -> None:
    payload = json.loads(_rupeevest_payload())
    valid = dict(payload["buys"]["stock_compare_data"][0])
    payload["buys"]["stock_compare_data"].extend(
        [
            dict(valid),
            {**valid, "fincode": 999999},
            {**valid, "day": "2026-08-11"},
        ]
    )

    parsed = parse_rupeevest_mf_flows(
        json.dumps(payload).encode(), last_modified="2026-08-10T16:00:00Z"
    )

    assert parsed["parser_state"] == "PARSED_STRUCTURED"
    assert parsed["record_count"] == 1
    assert parsed["output"]["duplicateRowCount"] == 1
    assert parsed["output"]["unmappedRowCount"] == 1
    assert parsed["output"]["invalidRowCount"] == 1


def test_pack5_parsers_are_deterministic() -> None:
    market_args = {
        "url": "https://www.nseindia.com/api/marketStatus",
        "last_modified": "2026-08-10T16:00:00Z",
    }
    flow_args = {
        "url": "https://www.rupeevest.com/Mutual-Fund-Holdings",
        "last_modified": "2026-08-10T16:00:00Z",
    }
    assert parse_nse_market_status(_market_payload(), **market_args) == parse_nse_market_status(
        _market_payload(), **market_args
    )
    assert parse_rupeevest_mf_flows(_rupeevest_payload(), **flow_args) == parse_rupeevest_mf_flows(
        _rupeevest_payload(), **flow_args
    )


def test_failed_pack5_refresh_cannot_replace_last_good(tmp_path) -> None:
    store = MarketDataStore(root=tmp_path / "objects", db_path=tmp_path / "market.sqlite3")
    store.initialize_schema()
    service = MarketDataService(store=store)
    fetched_at = datetime(2026, 8, 10, 16, tzinfo=timezone.utc)
    context = ParameterContext(
        trading_date=date(2026, 8, 10), market_session="CLOSED", now=fetched_at
    )
    contract = load_market_data_registry().by_key["nse_market_status"]

    good_raw = RawAcquisition.success(
        source_url=contract.canonical_url,
        status_code=200,
        media_type="application/json",
        content=_market_payload(),
        payload=None,
        fetched_at=fetched_at,
    )
    good = service._persist(
        service._normalize(contract, (good_raw,), context),
        context=context,
        run_id="good",
        slot="fixture",
    )
    bad_raw = good_raw.model_copy(update={"content": b'{"marketState":[]}'})
    bad = service._persist(
        service._normalize(contract, (bad_raw,), context),
        context=context,
        run_id="bad",
        slot="fixture",
    )

    latest = store.latest_for("nse_market_status")
    assert good.stored_attempt_id is not None
    assert bad.stored_attempt_id is not None
    assert latest is not None
    assert latest.attempt_id == good.stored_attempt_id
    assert latest.normalized_row_count == 1


@pytest.mark.parametrize(
    ("parser", "content", "state"),
    [
        (parse_nse_market_status, b"<html>blocked</html>", "WAIT_SCHEMA_MISMATCH"),
        (parse_nse_market_status, b'{"marketState":[]}', "WAIT_EMPTY_PARSE"),
        (parse_rupeevest_mf_flows, b"not-json", "WAIT_SCHEMA_MISMATCH"),
        (parse_rupeevest_mf_flows, b'{"search":{},"buys":{},"sells":{}}', "WAIT_SCHEMA_MISMATCH"),
    ],
)
def test_pack5_parsers_fail_closed(parser, content: bytes, state: str) -> None:
    parsed = parser(content, last_modified="2026-08-10T16:00:00Z")
    assert parsed["parser_state"] == state
    assert parsed["record_count"] == 0


def test_pack5_sources_are_registered_and_use_existing_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("nse_market_status", "rupeevest_mf_flows"):
        assert get_source_descriptor(key) is not None
        assert key in STRUCTURED_PARSERS
        assert key in PARSER_MAP

    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_nse_market_status",
        lambda: MultiStepFetchResult(True, "https://www.nseindia.com/api/marketStatus", 200, _market_payload(), "application/json", None),
    )
    resolved = resolve_and_fetch_source("nse_market_status", "https://www.nseindia.com/api/marketStatus")
    assert resolved.resolver_state == "NSE_MARKET_STATUS_COOKIE_API"
    assert resolved.content == _market_payload()

    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_rupeevest_mf_flows",
        lambda: MultiStepFetchResult(True, "https://www.rupeevest.com/Mutual-Fund-Holdings", 200, _rupeevest_payload(), "application/json", None),
    )
    resolved = resolve_and_fetch_source("rupeevest_mf_flows", "https://www.rupeevest.com/Mutual-Fund-Holdings")
    assert resolved.resolver_state == "RUPEEVEST_PUBLIC_MF_FLOW_BUNDLE"
    assert resolved.content == _rupeevest_payload()


def test_multistep_schema_failure_is_not_archived_as_http_200_new(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        phase3_multi_step_fetch,
        "fetch_nse_market_status",
        lambda: MultiStepFetchResult(
            False,
            "https://www.nseindia.com/api/marketStatus",
            200,
            b"",
            "application/json",
            "schema mismatch",
        ),
    )

    resolved = resolve_and_fetch_source(
        "nse_market_status", "https://www.nseindia.com/api/marketStatus"
    )

    assert resolved.status_code == 599
    assert resolved.resolver_state == "NSE_MARKET_STATUS_COOKIE_API_FAILED"
    assert resolved.content == b""
