from __future__ import annotations

import json
from datetime import UTC, date, datetime

from trendforge_api.derived_market_outputs import (
    CALCULATED_OUTPUT_KEYS,
    DerivedMarketOutputService,
    build_fundamental_ratios,
    build_industry_peer_groups,
    build_option_greeks,
    build_pcr_max_pain_observation,
)
from trendforge_api.market_data_store import MarketDataStore


ZERO_AUTHORITY = {
    "derived": True,
    "scoreEligible": False,
    "voteEligible": False,
    "canUnlockReady": False,
}


def _assert_zero_authority(row: dict) -> None:
    for key, value in ZERO_AUTHORITY.items():
        assert row[key] is value


def test_industry_peer_groups_use_exact_official_industry_only() -> None:
    records = [
        {"symbol": "AAA", "isin": "INE000A", "company": "A", "industry": "Banks"},
        {"symbol": "BBB", "isin": "INE000B", "company": "B", "industry": "Banks"},
        {"symbol": "CCC", "isin": "INE000C", "company": "C", "industry": "Power"},
        {"symbol": "NOIND", "isin": "INE000D", "company": "D", "industry": None},
    ]
    output = build_industry_peer_groups(
        records,
        data_date=date(2026, 8, 10),
        lineage_hash="a" * 64,
    )

    assert output["key"] == "industry_peer_group_v1"
    assert [row["symbol"] for row in output["records"]] == ["AAA", "BBB", "CCC"]
    assert output["records"][0]["peerSymbols"] == ["BBB"]
    assert output["records"][2]["peerSymbols"] == []
    assert output["records"][0]["lineageHashes"] == ["a" * 64]
    _assert_zero_authority(output["records"][0])


def test_option_greeks_require_rbi_rate_valid_expiry_and_positive_iv() -> None:
    option_rows = [
        {
            "symbol": "RELIANCE",
            "expiry": "25-Aug-2026",
            "strike": 1300,
            "optionType": "CE",
            "iv": 20.0,
            "underlyingValue": 1327.3,
            "lastPrice": 35.0,
        },
        {
            "symbol": "RELIANCE",
            "expiry": "25-Aug-2026",
            "strike": 1400,
            "optionType": "PE",
            "iv": 0.0,
            "underlyingValue": 1327.3,
        },
    ]
    rates = [
        {"tenorDays": 91, "annualRateDecimal": 0.05278},
        {"tenorDays": 182, "annualRateDecimal": 0.055501},
        {"tenorDays": 364, "annualRateDecimal": 0.056998},
    ]
    output = build_option_greeks(
        option_rows,
        rbi_rate_rows=rates,
        valuation_date=date(2026, 8, 10),
        lineage_hashes=("b" * 64, "c" * 64),
    )

    assert output["key"] == "option_greeks_calculated_v1"
    assert output["rejectedRowCount"] == 1
    assert len(output["records"]) == 1
    row = output["records"][0]
    assert row["riskFreeRate"] == 0.05278
    assert row["volatilityDecimal"] == 0.2
    assert row["model"] == "BLACK_SCHOLES_MERTON"
    assert row["rateSourceKey"] == "rbi_tbill_yield"
    assert row["dividendYieldAssumption"] == 0.0
    _assert_zero_authority(row)

    no_rate = build_option_greeks(
        option_rows,
        rbi_rate_rows=[],
        valuation_date=date(2026, 8, 10),
        lineage_hashes=("b" * 64,),
    )
    assert no_rate["records"] == []
    assert no_rate["state"] == "WAIT_REQUIRED_INPUT"


def test_pcr_max_pain_is_one_observation_per_real_snapshot() -> None:
    rows = [
        {"symbol": "ABC", "expiry": "27-Aug-2026", "strike": 90, "optionType": "CE", "openInterest": 100},
        {"symbol": "ABC", "expiry": "27-Aug-2026", "strike": 100, "optionType": "CE", "openInterest": 200},
        {"symbol": "ABC", "expiry": "27-Aug-2026", "strike": 90, "optionType": "PE", "openInterest": 150},
        {"symbol": "ABC", "expiry": "27-Aug-2026", "strike": 100, "optionType": "PE", "openInterest": 150},
    ]
    output = build_pcr_max_pain_observation(
        rows,
        data_date=date(2026, 8, 10),
        lineage_hash="d" * 64,
    )

    assert output["key"] == "pcr_max_pain_history_v1"
    assert output["historyPolicy"] == "PROSPECTIVE_OBSERVED_SNAPSHOTS_ONLY"
    assert len(output["records"]) == 1
    row = output["records"][0]
    assert row["pcrOi"] == 1.0
    assert row["maxPainStrike"] in {90.0, 100.0}
    assert row["observedDate"] == "2026-08-10"
    assert row["observationId"].startswith("ABC|2026-08-27|2026-08-10|")
    _assert_zero_authority(row)


def test_fundamental_ratios_fail_closed_and_never_zero_fill() -> None:
    facts = [
        {
            "symbol": "ABC",
            "periodEnd": "2026-03-31",
            "profitAfterTaxCr": 100,
            "totalEquityCr": 500,
            "totalAssetsCr": 1000,
            "totalDebtCr": 250,
            "eps": 10,
        },
        {"symbol": "MISSING", "periodEnd": "2026-03-31", "profitAfterTaxCr": 10},
    ]
    market = [{"symbol": "ABC", "close": 200, "marketCapCr": 2000}]
    output = build_fundamental_ratios(
        facts,
        market_rows=market,
        data_date=date(2026, 3, 31),
        lineage_hashes=("e" * 64, "f" * 64),
    )

    assert output["key"] == "fundamental_ratios_v1"
    assert len(output["records"]) == 1
    row = output["records"][0]
    assert row["pe"] == 20.0
    assert row["pb"] == 4.0
    assert row["roePct"] == 20.0
    assert row["roaPct"] == 10.0
    assert row["debtToEquity"] == 0.5
    assert row["missingMetrics"] == []
    _assert_zero_authority(row)
    assert output["rejectedRowCount"] == 1


def test_materializer_persists_only_available_calculated_outputs(tmp_path) -> None:
    store = MarketDataStore(root=tmp_path / "objects", db_path=tmp_path / "market.db")
    now = datetime(2026, 8, 10, 10, tzinfo=UTC)

    def save(key: str, payload: dict, rows: int, data_date: date) -> None:
        store.commit_success(
            run_id="source-run",
            source_key=key,
            trading_date=data_date,
            slot="test",
            attempted_at=now,
            fetched_at=now,
            data_date=data_date,
            source_url=f"fixture://{key}",
            http_status=200,
            media_type="application/json",
            content=json.dumps(payload, sort_keys=True).encode(),
            extension="json",
            normalized_row_count=rows,
            retry_count=0,
        )

    save(
        "nse_nifty500_constituents",
        {"sourceKey": "nse_nifty500_constituents", "dataDate": "2026-08-10", "records": [
            {"symbol": "AAA", "isin": "INEA", "company": "A", "industry": "Banks"},
            {"symbol": "BBB", "isin": "INEB", "company": "B", "industry": "Banks"},
        ]},
        2,
        date(2026, 8, 10),
    )
    save(
        "nse_option_chain_equity",
        {"sourceKey": "nse_option_chain_equity", "dataDate": "2026-08-10", "records": [
            {"symbol": "ABC", "expiry": "27-Aug-2026", "strike": 100, "optionType": "CE", "openInterest": 100, "iv": 20, "underlyingValue": 101},
            {"symbol": "ABC", "expiry": "27-Aug-2026", "strike": 100, "optionType": "PE", "openInterest": 120, "iv": 21, "underlyingValue": 101},
        ]},
        2,
        date(2026, 8, 10),
    )
    save(
        "rbi_tbill_yield",
        {"sourceKey": "rbi_tbill_yield", "dataDate": "2026-08-05", "records": [
            {"tenorDays": 91, "annualRateDecimal": 0.05278},
            {"tenorDays": 182, "annualRateDecimal": 0.055501},
            {"tenorDays": 364, "annualRateDecimal": 0.056998},
        ]},
        3,
        date(2026, 8, 5),
    )

    service = DerivedMarketOutputService(store=store)
    result = service.materialize(run_id="derived-run", at=now, trading_date=date(2026, 8, 10), slot="test")

    assert set(result) == {
        "industry_peer_group_v1",
        "option_greeks_calculated_v1",
        "pcr_max_pain_history_v1",
    }
    assert "fundamental_ratios_v1" not in result
    assert set(result).issubset(CALCULATED_OUTPUT_KEYS)
    assert all(store.latest_for(key) is not None for key in result)
    assert store.latest_for("fundamental_ratios_v1") is None

