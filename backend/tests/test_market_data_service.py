from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from trendforge_api.market_data_registry import load_market_data_registry
from trendforge_api.market_data_service import (
    AcquisitionState,
    MarketDataService,
    ParameterContext,
    ParsedSourcePayload,
    RawAcquisition,
)
from trendforge_api.market_data_store import ManifestStatus, MarketDataStore


NOW = datetime(2026, 8, 5, 4, 0, tzinfo=UTC)  # 09:30 IST


class FakeTransport:
    def __init__(
        self,
        *,
        failures: set[str] | None = None,
        delay: float = 0,
        empty: bool = False,
    ) -> None:
        self.failures = failures or set()
        self.delay = delay
        self.empty = empty
        self.calls: list[tuple[str, str, dict[str, str]]] = []
        self.active = 0
        self.max_active = 0

    async def fetch_endpoint(
        self, endpoint_key: str, parameters: dict[str, str]
    ) -> RawAcquisition:
        self.calls.append(("endpoint", endpoint_key, parameters))
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if endpoint_key in self.failures:
                return RawAcquisition.failed(
                    source_url=f"https://www.nseindia.com/{endpoint_key}",
                    error="fixture failure",
                    retry_count=3,
                )
            payload = [] if self.empty else [{"symbol": endpoint_key.upper()}]
            body = json.dumps({"data": payload}).encode()
            return RawAcquisition.success(
                source_url=f"https://www.nseindia.com/{endpoint_key}",
                status_code=200,
                media_type="application/json",
                content=body,
                payload={"data": payload},
                fetched_at=NOW,
            )
        finally:
            self.active -= 1

    async def fetch_resolver(
        self, source_key: str, catalog_url: str, trading_date=None
    ) -> RawAcquisition:
        self.calls.append(("resolver", source_key, {"trading_date": trading_date}))
        if source_key in self.failures:
            return RawAcquisition.failed(
                source_url=catalog_url,
                error="fixture failure",
                retry_count=2,
            )
        body = json.dumps({"data": [] if self.empty else [{"symbol": source_key}]}).encode()
        return RawAcquisition.success(
            source_url=catalog_url,
            status_code=200,
            media_type="application/json",
            content=body,
            payload=json.loads(body),
            fetched_at=NOW,
        )


def fixture_normalizer(contract, acquisitions, _context) -> ParsedSourcePayload:
    if not acquisitions or any(item.state is AcquisitionState.FAILED for item in acquisitions):
        return ParsedSourcePayload(parser_state="FETCH_FAILED", records=(), error="fixture failure")
    rows: list[dict[str, Any]] = []
    for acquisition in acquisitions:
        data = acquisition.payload.get("data", []) if isinstance(acquisition.payload, dict) else []
        rows.extend(row for row in data if isinstance(row, dict))
    return ParsedSourcePayload(
        parser_state="PARSED_STRUCTURED",
        records=tuple(rows),
        data_date=date(2026, 8, 5),
        payload={"sourceKey": contract.source_key, "rows": rows},
    )


def _context(**changes: Any) -> ParameterContext:
    values = {
        "trading_date": date(2026, 8, 5),
        "market_session": "OPEN",
        "symbols": ("RELIANCE", "TCS"),
        "scrip_codes": {"RELIANCE": "500325", "TCS": "532540"},
        "sector_indices": ("NIFTY 50",),
        "option_expiries": {
            "RELIANCE": "25-Aug-2026",
            "TCS": "25-Aug-2026",
        },
    }
    values.update(changes)
    return ParameterContext(**values)


def test_all_69_contracts_have_supported_normalizers() -> None:
    registry = load_market_data_registry()
    service = MarketDataService(transport=FakeTransport())
    unsupported = [
        contract.source_key
        for contract in registry.contracts
        if not service.supports_normalizer(contract)
    ]
    assert unsupported == []


def test_parameter_providers_build_required_fanout_and_fail_closed() -> None:
    registry = load_market_data_registry()
    service = MarketDataService(transport=FakeTransport())
    symbol_contract = registry.by_key["nse_option_chain_equity"]
    requests = service.build_parameter_sets(symbol_contract, _context())
    assert requests == (
        {"symbol": "RELIANCE", "expiry": "25-Aug-2026"},
        {"symbol": "TCS", "expiry": "25-Aug-2026"},
    )

    with pytest.raises(ValueError, match="requires bounded option symbols"):
        service.build_parameter_sets(symbol_contract, _context(option_expiries={}))


def test_market_wide_replacements_and_pit_symbol_fanout_parameters() -> None:
    registry = load_market_data_registry()
    service = MarketDataService(transport=FakeTransport())

    assert service.build_parameter_sets(
        registry.by_key["bse_corporate_announcements"], _context()
    ) == ({"from_date": "05/08/2026", "to_date": "05/08/2026"},)
    assert service.build_parameter_sets(
        registry.by_key["nse_pit_symbol"], _context(symbols=("RELIANCE", "INFY"))
    ) == ({"symbol": "RELIANCE"}, {"symbol": "INFY"})
    with pytest.raises(ValueError, match="requires symbols for fan-out"):
        service.build_parameter_sets(
            registry.by_key["nse_pit_symbol"], _context(symbols=())
        )
    assert service.build_parameter_sets(
        registry.by_key["nse_shareholding_pattern"], _context()
    ) == ({},)


def test_successful_transport_note_is_not_promoted_to_result_error() -> None:
    registry = load_market_data_registry()
    service = MarketDataService(transport=FakeTransport())
    raw = RawAcquisition.success(
        source_url="https://www.nseindia.com/api/corporates-pit?index=equities&symbol=INFY",
        status_code=200,
        media_type="application/json",
        content=json.dumps(
            {
                "data": [
                    {
                        "did": "1",
                        "symbol": "INFY",
                        "company": "Infosys Limited",
                        "acqName": "Employee Trust",
                        "date": "06-Apr-2026 16:07",
                        "tdpTransactionType": "Buy",
                    }
                ]
            }
        ).encode(),
        payload=None,
        fetched_at=NOW,
    ).model_copy(update={"error": "Raw response archived; parser still required."})

    result = service._normalize(
        registry.by_key["nse_pit_symbol"], (raw,), _context()
    )

    assert result.normalized_row_count == 1
    assert result.error is None


def test_response_reuse_fetches_pr_zip_once_but_normalizes_three_sources() -> None:
    registry = load_market_data_registry()
    contracts = tuple(
        registry.by_key[key]
        for key in (
            "nse_bhavcopy_eod",
            "nse_trade_to_trade",
            "nse_pr_market_snapshot",
        )
    )
    transport = FakeTransport()
    service = MarketDataService(transport=transport, normalizer=fixture_normalizer)

    results = asyncio.run(service.run_sources(contracts, context=_context()))

    assert set(results) == {item.source_key for item in contracts}
    assert len(transport.calls) == 1
    assert all(result.status is ManifestStatus.SUCCESS_NEW for result in results.values())


def test_session_sharing_keeps_separate_responses() -> None:
    registry = load_market_data_registry()
    contracts = tuple(
        registry.by_key[key]
        for key in ("nse_most_active_volume", "nse_most_active_value")
    )
    transport = FakeTransport()
    service = MarketDataService(transport=transport, normalizer=fixture_normalizer)

    asyncio.run(service.run_sources(contracts, context=_context()))

    assert Counter(call[1] for call in transport.calls) == {
        "nse_most_active_volume": 1,
        "nse_most_active_value": 1,
    }


def test_one_source_failure_does_not_cancel_other_sources() -> None:
    registry = load_market_data_registry()
    contracts = tuple(
        registry.by_key[key]
        for key in ("bse_sast", "nse_oi_spurts", "nse_all_indices")
    )
    transport = FakeTransport(failures={"nse_oi_spurts"})
    service = MarketDataService(transport=transport, normalizer=fixture_normalizer)

    results = asyncio.run(service.run_sources(contracts, context=_context()))

    assert results["nse_oi_spurts"].status is ManifestStatus.FAILED
    assert results["bse_sast"].status is ManifestStatus.SUCCESS_NEW
    assert results["nse_all_indices"].status is ManifestStatus.SUCCESS_NEW


def test_global_and_domain_concurrency_caps_are_observed() -> None:
    registry = load_market_data_registry()
    contracts = tuple(
        registry.by_key[key]
        for key in (
            "nse_live_equity_derivatives_banknifty_fut",
            "nse_live_equity_derivatives_banknifty_opt",
            "nse_live_equity_derivatives_index_fut",
            "nse_live_equity_derivatives_index_opt",
        )
    )
    transport = FakeTransport(delay=0.02)
    service = MarketDataService(
        transport=transport,
        normalizer=fixture_normalizer,
        global_concurrency=3,
        domain_caps={"www.nseindia.com": 1},
    )

    asyncio.run(service.run_sources(contracts, context=_context()))

    assert transport.max_active == 1


def test_circuit_breaker_stops_repeated_domain_failures() -> None:
    registry = load_market_data_registry()
    contract = registry.by_key["nse_oi_spurts"]
    transport = FakeTransport(failures={"nse_oi_spurts"})
    service = MarketDataService(
        transport=transport,
        normalizer=fixture_normalizer,
        breaker_failure_threshold=2,
        breaker_cooldown_seconds=900,
    )

    first = asyncio.run(service.run_source(contract, context=_context()))
    second = asyncio.run(service.run_source(contract, context=_context()))
    third = asyncio.run(service.run_source(contract, context=_context()))

    assert first.status is ManifestStatus.FAILED
    assert second.status is ManifestStatus.FAILED
    assert third.status is ManifestStatus.FAILED
    assert "circuit breaker" in (third.error or "").lower()
    assert len(transport.calls) == 2


def test_queued_same_domain_calls_recheck_open_circuit() -> None:
    registry = load_market_data_registry()
    keys = (
        "nse_live_equity_derivatives_banknifty_fut",
        "nse_live_equity_derivatives_banknifty_opt",
        "nse_live_equity_derivatives_index_fut",
        "nse_live_equity_derivatives_index_opt",
    )
    contracts = tuple(registry.by_key[key] for key in keys)
    transport = FakeTransport(failures=set(keys), delay=0.01)
    service = MarketDataService(
        transport=transport,
        normalizer=fixture_normalizer,
        domain_caps={"www.nseindia.com": 1},
        breaker_failure_threshold=2,
    )

    results = asyncio.run(service.run_sources(contracts, context=_context()))

    assert len(transport.calls) == 2
    assert all(result.status is ManifestStatus.FAILED for result in results.values())
    assert sum("circuit breaker" in (result.error or "").lower() for result in results.values()) == 2


@pytest.mark.parametrize(
    ("source_key", "expected"),
    [
        ("bse_sast", ManifestStatus.VALID_EMPTY),
        ("nse_large_deals", ManifestStatus.WAITING_FOR_PUBLICATION),
        ("fred_real_yield_10y", ManifestStatus.FAILED),
    ],
)
def test_empty_rules_are_contract_specific(source_key: str, expected: ManifestStatus) -> None:
    registry = load_market_data_registry()
    transport = FakeTransport(empty=True)
    service = MarketDataService(transport=transport, normalizer=fixture_normalizer)

    result = asyncio.run(
        service.run_source(registry.by_key[source_key], context=_context())
    )

    assert result.status is expected


def test_validated_success_persists_and_failure_preserves_last_good(tmp_path: Path) -> None:
    registry = load_market_data_registry()
    contract = registry.by_key["nse_oi_spurts"]
    store = MarketDataStore(root=tmp_path / "market_data", db_path=tmp_path / "temp.db")
    transport = FakeTransport()
    service = MarketDataService(
        transport=transport,
        normalizer=fixture_normalizer,
        store=store,
    )
    context = _context()

    good = asyncio.run(service.run_source(contract, context=context, run_id="good", slot="0917"))
    transport.failures.add("nse_oi_spurts")
    failed = asyncio.run(service.run_source(contract, context=context, run_id="bad", slot="1030"))

    latest = store.latest_for("nse_oi_spurts")
    assert good.stored_attempt_id == latest.attempt_id
    assert failed.status is ManifestStatus.FAILED
    assert latest.run_id == "good"


def test_default_structured_adapter_normalizes_real_board_fixture() -> None:
    registry = load_market_data_registry()
    contract = registry.by_key["nse_board_meetings"]

    class BoardTransport(FakeTransport):
        async def fetch_resolver(
            self, source_key: str, catalog_url: str, trading_date=None
        ) -> RawAcquisition:
            row = {
                "bm_symbol": "ALPHA",
                "bm_date": "14-Aug-2026",
                "bm_purpose": "Financial Results",
                "bm_desc": "Quarterly results",
            }
            content = json.dumps([row]).encode()
            return RawAcquisition.success(
                source_url=catalog_url,
                status_code=200,
                media_type="application/json",
                content=content,
                payload=[row],
                fetched_at=NOW,
            )

    service = MarketDataService(transport=BoardTransport())
    result = asyncio.run(service.run_source(contract, context=_context()))

    assert result.status is ManifestStatus.SUCCESS_NEW
    assert result.normalized_row_count == 1
    assert result.records[0]["symbol"] == "ALPHA"


@pytest.mark.parametrize(
    ("source_key", "payload"),
    [
        (
            "bse_bulk_deals",
            {
                "Table": [
                    {
                        "DEAL_DATE": "2026-08-05T00:00:00",
                        "SCRIP_CODE": 512591,
                        "scripname": "ALPHA",
                        "CLIENT_NAME": "FUND A",
                        "TRANSACTION_TYPE": "P",
                        "QUANTITY": 1000,
                        "PRICE": 12.5,
                    }
                ]
            },
        ),
        (
            "nse_financial_results",
            {"data": [{"symbol": "ALPHA", "periodEnded": "30-Jun-2026"}]},
        ),
        (
            "nse_most_active_value",
            {
                "timestamp": "05-Aug-2026 09:29:00",
                "data": [{"symbol": "ALPHA", "lastPrice": 100, "pChange": 1.2}],
            },
        ),
    ],
)
def test_default_named_adapter_families_emit_records(
    source_key: str, payload: dict[str, Any]
) -> None:
    registry = load_market_data_registry()
    contract = registry.by_key[source_key]

    class PayloadTransport(FakeTransport):
        async def fetch_endpoint(
            self, endpoint_key: str, parameters: dict[str, str]
        ) -> RawAcquisition:
            content = json.dumps(payload).encode()
            return RawAcquisition.success(
                source_url=f"https://www.nseindia.com/{endpoint_key}",
                status_code=200,
                media_type="application/json",
                content=content,
                payload=payload,
                fetched_at=NOW,
            )

    service = MarketDataService(transport=PayloadTransport())
    result = asyncio.run(service.run_source(contract, context=_context()))

    assert result.parser_state == "PARSED_ADAPTER"
    assert result.normalized_row_count >= 1


def test_verified_transport_empty_uses_contract_empty_semantics() -> None:
    registry = load_market_data_registry()
    contract = registry.by_key["bse_sast"]

    class ValidEmptyTransport(FakeTransport):
        async def fetch_endpoint(
            self, endpoint_key: str, parameters: dict[str, str]
        ) -> RawAcquisition:
            return RawAcquisition(
                state=AcquisitionState.VALID_EMPTY,
                source_url=f"https://www.nseindia.com/{endpoint_key}",
                status_code=200,
                media_type="application/json",
                content=b"[]",
                payload=[],
                fetched_at=NOW,
            )

    service = MarketDataService(
        transport=ValidEmptyTransport(),
        normalizer=lambda *_: ParsedSourcePayload(
            parser_state="WAIT_SCHEMA_MISMATCH",
            records=(),
        ),
    )
    result = asyncio.run(service.run_source(contract, context=_context()))

    assert result.status is ManifestStatus.VALID_EMPTY


@pytest.mark.parametrize(
    ("parser_state", "data_date"),
    [
        ("WAIT_SCHEMA_MISMATCH", date(2026, 8, 5)),
        ("PARSED_STRUCTURED", date(2026, 8, 6)),
    ],
)
def test_failed_or_future_parser_rows_are_quarantined(
    parser_state: str, data_date: date
) -> None:
    registry = load_market_data_registry()
    contract = registry.by_key["nse_oi_spurts"]
    service = MarketDataService(
        transport=FakeTransport(),
        normalizer=lambda *_: ParsedSourcePayload(
            parser_state=parser_state,
            records=({"symbol": "POISONED"},),
            data_date=data_date,
        ),
    )

    result = asyncio.run(service.run_source(contract, context=_context()))

    assert result.status is ManifestStatus.FAILED
