from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import trendforge_api.main as main_module
from trendforge_api.fii_stock_signals import (
    APPROVED_SOURCE_KEYS,
    CanonicalLatestResultLoader,
    FIIStockSignalsSnapshot,
    WARNING,
    build_fii_stock_signals,
)
from trendforge_api.main import app


NOW = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)


def parsed(
    source_key: str,
    rows: list[dict],
    *,
    container: str = "rows",
    state: str = "PARSED_STRUCTURED",
    data_date: str = "2026-08-10",
) -> dict:
    return {
        "sourceKey": source_key,
        "parserState": state,
        "dataDate": data_date,
        "output": {container: rows},
    }


def loader_for(results: dict[str, dict], calls: list[str] | None = None):
    def load(source_key: str):
        if calls is not None:
            calls.append(source_key)
        return results.get(source_key)

    return load


def test_large_deals_normalize_aliases_without_fii_attribution() -> None:
    calls: list[str] = []
    results = {
        "nse_large_deals": parsed(
            "nse_large_deals",
            [
                {
                    "symbol": "reliance",
                    "dealType": "BULK",
                    "date": "2026-08-10",
                    "buyer": "NAMED FUND A",
                    "quantity": 100,
                    "price": 25,
                },
                {
                    "symbol": "SHORTROW",
                    "dealType": "SHORT",
                    "date": "2026-08-10",
                    "clientName": "CLIENT",
                    "side": "BUY",
                    "quantity": 1,
                    "price": 1,
                },
            ],
            container="deals",
        ),
        "nse_bulk_deals_today_csv": parsed(
            "nse_bulk_deals_today_csv",
            [
                {
                    "Symbol": "TCS",
                    "Buy/Sell": "S",
                    "Client Name": "CLIENT B",
                    "Quantity Traded": "2,000",
                    "Trade Price / Wght. Avg. Price": "100.5",
                    "date": "10-AUG-2026",
                }
            ],
        ),
        "bse_bulk_deals": parsed(
            "bse_bulk_deals",
            [
                {
                    "symbol": "INFY",
                    "TRANSACTION_TYPE": "P",
                    "CLIENT_NAME": "CLIENT C",
                    "QUANTITY": 10,
                    "PRICE": 50,
                    "DEAL_DATE": "10/08/2026",
                },
                {
                    "SCRIP_CODE": "500325",
                    "scripname": "Reliance Industries",
                    "TRANSACTION_TYPE": "P",
                    "DEAL_DATE": "10/08/2026",
                },
            ],
        ),
    }

    snapshot = build_fii_stock_signals(
        loader=loader_for(results, calls), generated_at=NOW
    )

    assert set(APPROVED_SOURCE_KEYS).issubset(calls)
    assert "tickertape_fii_holding_change_3m" in calls
    assert "dhan_fii_holding_change" in calls
    assert "screener_in_fii_holding_change" in calls
    assert "equitymaster_fii_buys_reference" in calls
    assert [item.symbol for item in snapshot.large_deals] == ["INFY", "TCS", "RELIANCE"]
    by_symbol = {item.symbol: item for item in snapshot.large_deals}
    assert by_symbol["RELIANCE"].side == "BUY"
    assert by_symbol["RELIANCE"].client == "NAMED FUND A"
    assert by_symbol["RELIANCE"].value == 2500
    assert by_symbol["TCS"].side == "SELL"
    assert by_symbol["TCS"].value == 201000
    assert by_symbol["INFY"].deal_type == "BULK"
    assert "FII" not in by_symbol["INFY"].model_dump()
    assert "not certified FII" in snapshot.warning
    assert snapshot.symbols == ["INFY", "RELIANCE", "TCS"]


def test_deal_validation_deduplicates_and_preserves_missing_numbers_as_null() -> None:
    duplicate = {
        "symbol": "HDFCBANK",
        "dealType": "BLOCK",
        "date": "2026-08-10",
        "side": "B",
        "client": "CLIENT A",
        "quantity": "bad",
        "price": -1,
    }
    results = {
        "nse_large_deals_snapshot": parsed(
            "nse_large_deals_snapshot", [duplicate, dict(duplicate)]
        )
    }

    snapshot = build_fii_stock_signals(loader=loader_for(results), generated_at=NOW)

    assert len(snapshot.large_deals) == 1
    deal = snapshot.large_deals[0]
    assert deal.quantity is None
    assert deal.price is None
    assert deal.value is None


def test_quarterly_fii_changes_require_explicit_change_evidence() -> None:
    results = {
        "nse_shareholding_pattern": parsed(
            "nse_shareholding_pattern",
            [
                {
                    "symbol": "TCS",
                    "date": "2026-06-30",
                    "fiiHoldingPct": 12.3,
                    "previousFiiPct": 11.8,
                },
                {
                    "symbol": "INFY",
                    "date": "2026-06-30",
                    "fpiPct": 18.2,
                    "fpiPctChange": -0.25,
                },
                {
                    "symbol": "CURRENTONLY",
                    "date": "2026-06-30",
                    "fiiPct": 10.0,
                },
                {
                    "symbol": "PUBLICONLY",
                    "date": "2026-06-30",
                    "public_val": 45.0,
                    "pr_and_prgrp": 55.0,
                },
            ],
        )
    }

    snapshot = build_fii_stock_signals(loader=loader_for(results), generated_at=NOW)

    assert [item.symbol for item in snapshot.fii_holding_changes] == ["INFY", "TCS"]
    by_symbol = {item.symbol: item for item in snapshot.fii_holding_changes}
    assert by_symbol["TCS"].fii_pct_change == 0.5
    assert by_symbol["INFY"].fii_pct_change == -0.25
    assert all(item.scope == "QUARTERLY_OWNERSHIP_ONLY" for item in snapshot.fii_holding_changes)


def test_missing_wait_and_malformed_results_fail_closed() -> None:
    results = {
        "nse_large_deals": parsed(
            "nse_large_deals",
            [{"symbol": "RELIANCE"}],
            state="WAIT_STALE_DATA",
        ),
        "bse_bulk_deals": {
            "sourceKey": "bse_bulk_deals",
            "parserState": "PARSED_STRUCTURED",
            "dataDate": "2026-08-10",
            "output": "not-a-dict",
        },
    }

    snapshot = build_fii_stock_signals(loader=loader_for(results), generated_at=NOW)

    assert snapshot.large_deals == []
    assert snapshot.fii_holding_changes == []
    assert snapshot.symbols == []


def test_api_smoke_returns_camel_case_signal_and_symbol(monkeypatch) -> None:
    snapshot = build_fii_stock_signals(
        loader=loader_for(
            {
                "nse_large_deals": parsed(
                    "nse_large_deals",
                    [
                        {
                            "symbol": "RELIANCE",
                            "dealType": "BULK",
                            "date": "2026-08-10",
                            "side": "BUY",
                            "client": "CLIENT A",
                            "quantity": 10,
                            "price": 20,
                        }
                    ],
                )
            }
        ),
        generated_at=NOW,
    )
    monkeypatch.setattr(
        main_module, "build_fii_stock_signals", lambda **_kwargs: snapshot
    )

    response = TestClient(app).get("/api/institutional/fii-stock-signals")

    assert response.status_code == 200
    payload = response.json()
    assert payload["warning"] == WARNING
    assert payload["largeDeals"][0]["signalType"] == "LARGE_DEAL"
    assert payload["largeDeals"][0]["symbol"] == "RELIANCE"
    assert payload["fiiHoldingChanges"] == []
    assert payload["symbols"] == ["RELIANCE"]
    assert FIIStockSignalsSnapshot.model_validate(payload)


def test_canonical_latest_loader_prefers_refresh_object_and_preserves_fetch_time(
    tmp_path,
) -> None:
    payload = {
        "sourceKey": "nse_bulk_deals_today_csv",
        "parserState": "PARSED_STRUCTURED",
        "dataDate": "2026-08-11",
        "records": [
            {
                "symbol": "TCS",
                "Buy/Sell": "BUY",
                "Client Name": "CLIENT NEW",
                "Quantity Traded": "10",
                "Trade Price / Wght. Avg. Price": "20",
                "Date": "11-AUG-2026",
            }
        ],
    }
    content = json.dumps(payload, sort_keys=True).encode("utf-8")
    content_hash = hashlib.sha256(content).hexdigest()
    object_path = tmp_path / "objects" / content_hash[:2] / f"{content_hash}.json"
    object_path.parent.mkdir(parents=True)
    object_path.write_bytes(content)
    attempt = SimpleNamespace(
        source_key="nse_bulk_deals_today_csv",
        object_path=str(object_path),
        content_hash=content_hash,
        data_date=datetime(2026, 8, 11, tzinfo=UTC).date(),
        fetched_at=datetime(2026, 8, 11, 12, 34, 56, tzinfo=UTC),
    )
    fallback_calls: list[str] = []

    class Store:
        root = tmp_path

        @staticmethod
        def latest_all():
            return {attempt.source_key: attempt}

    loader = CanonicalLatestResultLoader(
        Store(),
        fallback=lambda key: fallback_calls.append(key) or None,
    )
    snapshot = build_fii_stock_signals(loader=loader, generated_at=NOW)

    assert [item.symbol for item in snapshot.large_deals] == ["TCS"]
    assert snapshot.large_deals[0].fetched_at == attempt.fetched_at
    assert snapshot.latest_fetched_at == attempt.fetched_at
    assert attempt.source_key not in fallback_calls


def test_canonical_latest_loader_fails_closed_on_hash_mismatch(tmp_path) -> None:
    object_path = tmp_path / "objects" / "aa" / "bad.json"
    object_path.parent.mkdir(parents=True)
    object_path.write_text('{"records": []}', encoding="utf-8")
    attempt = SimpleNamespace(
        source_key="nse_large_deals",
        object_path=str(object_path),
        content_hash="0" * 64,
        data_date=datetime(2026, 8, 11, tzinfo=UTC).date(),
        fetched_at=NOW,
    )
    fallback_calls: list[str] = []

    class Store:
        root = tmp_path

        @staticmethod
        def latest_all():
            return {attempt.source_key: attempt}

    loader = CanonicalLatestResultLoader(
        Store(),
        fallback=lambda key: fallback_calls.append(key) or None,
    )
    snapshot = build_fii_stock_signals(loader=loader, generated_at=NOW)

    assert snapshot.large_deals == []
    assert attempt.source_key not in fallback_calls


def test_tickertape_and_dhan_screens_become_info_holdings_not_certified_fii() -> None:
    snapshot = build_fii_stock_signals(
        loader=loader_for(
            {
                "nse_nifty500_constituents": parsed(
                    "nse_nifty500_constituents",
                    [
                        {
                            "Company Name": "Infosys Limited",
                            "Symbol": "INFY",
                            "ISIN Code": "INE009A01021",
                        },
                        {
                            "Company Name": "Tata Consultancy Services Limited",
                            "Symbol": "TCS",
                            "ISIN Code": "INE467B01029",
                        },
                    ],
                ),
                "tickertape_fii_holding_change_3m": parsed(
                    "tickertape_fii_holding_change_3m",
                    [
                        {
                            "name": "Infosys",
                            "symbol": "INFY",
                            "fiiHoldPct": 31.2,
                            "fiiChgPct": 0.4,
                        }
                    ],
                ),
                "dhan_fii_holding_change": parsed(
                    "dhan_fii_holding_change",
                    [{"name": "TCS", "symbol": "TCS", "fiiChgPct": 3.1}],
                ),
                "screener_in_fii_holding_change": parsed(
                    "screener_in_fii_holding_change",
                    [
                        {"name": "Infosys Limited", "symbol": None, "fiiChgPct": 1.2},
                        {"name": "Unknown Shell Co", "symbol": None, "fiiChgPct": 2.0},
                    ],
                ),
                "equitymaster_fii_buys_reference": parsed(
                    "equitymaster_fii_buys_reference",
                    [
                        {"name": "Tata Consultancy Services Limited", "fiiChgPct": 0.8},
                        {"name": "Infosys Limited"},
                        {"name": "Infosys Limited"},
                    ],
                ),
            }
        ),
        generated_at=NOW,
    )
    infy = next(item for item in snapshot.fii_holding_changes if item.symbol == "INFY" and item.source_key == "tickertape_fii_holding_change_3m")
    dhan = next(item for item in snapshot.fii_holding_changes if item.symbol == "TCS" and item.source_key == "dhan_fii_holding_change")
    assert infy.fii_pct == 31.2
    assert infy.identity_status == "TICKER_IN_UNIVERSE"
    assert dhan.fii_pct is None
    assert dhan.holding_level_note == "holding level not supplied"
    assert dhan.fii_pct_change == 3.1
    mapped = [
        item
        for item in snapshot.fii_holding_changes
        if item.source_key == "screener_in_fii_holding_change" and item.symbol == "INFY"
    ]
    assert mapped and mapped[0].identity_status == "NAME_MAPPED"
    unresolved = [
        item
        for item in snapshot.fii_holding_changes
        if item.company_name == "Unknown Shell Co"
    ]
    assert unresolved and unresolved[0].symbol is None
    assert unresolved[0].identity_status == "NAME_ONLY"
    assert "Unknown Shell Co" not in snapshot.symbols
    assert "not certified FII" in snapshot.warning
