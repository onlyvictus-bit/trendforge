"""Unit tests for NSE liveEquity-derivatives fan-out aggregator."""
from __future__ import annotations

from types import SimpleNamespace

import asyncio

from trendforge_api.derivatives_fanout import (
    DERIVATIVES_CHILD_KEYS,
    _rows_from_payload,
    fanout_to_dict,
)
from trendforge_api.institutional_sources import FetchState


def test_contract_dedupe_preserves_child_identity() -> None:
    payload = {
        "timestamp": "31-Jul-2026 15:30:00",
        "data": [
            {
                "identifier": "OPTSTKM&M25-08-2026CE3400.00",
                "underlying": "M&M",
                "strikePrice": 3400,
                "optionType": "Call",
                "openInterest": 10,
            }
        ],
    }
    rows = _rows_from_payload(payload, "nse_live_equity_derivatives_stock_opt")
    assert len(rows) == 1
    assert rows[0]["_source_key"] == "nse_live_equity_derivatives_stock_opt"
    assert rows[0]["_index"] == "stock_opt"
    assert rows[0]["_contract_id"] == "OPTSTKM&M25-08-2026CE3400.00"


def test_child_keys_cover_all_indexes() -> None:
    assert len(DERIVATIVES_CHILD_KEYS) == 6
    assert any("stock_opt" in key for key in DERIVATIVES_CHILD_KEYS)
    assert any("banknifty" in key for key in DERIVATIVES_CHILD_KEYS)


def test_fanout_marks_alias_only_and_aggregates() -> None:
    from trendforge_api import derivatives_fanout as mod

    class FakeClient:
        async def fetch(self, key, parameters=None, force=False):  # noqa: ANN001
            del parameters, force
            payload = {
                "timestamp": "t",
                "data": [
                    {
                        "identifier": f"ID-{key}",
                        "underlying": "X",
                        "strikePrice": 1,
                        "optionType": "Call",
                        "openInterest": 1,
                    }
                ],
            }
            return SimpleNamespace(
                state=FetchState.RAW_ARCHIVED,
                url=f"https://www.nseindia.com/api/liveEquity-derivatives?index={key}",
                status_code=200,
                raw_path=f"/tmp/{key}.json",
                record_count=1,
                payload=payload,
                reason="ok",
            )

    result = asyncio.run(
        mod.fetch_derivatives_fanout(FakeClient())  # type: ignore[arg-type]
    )
    assert result.alias_only is True
    assert result.classification == "POPULATED_USABLE"
    assert result.record_count == 6
    doc = fanout_to_dict(result)
    assert doc["alias_key"] == "nse_live_equity_derivatives"
    assert len(doc["child_results"]) == 6
