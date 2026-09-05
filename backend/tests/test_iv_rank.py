from __future__ import annotations

from datetime import date, timedelta

from trendforge_api.iv_rank import calculate_iv_rank, select_atm_iv_observation


def test_select_atm_iv_supports_exchange_and_provider_shapes() -> None:
    exchange = select_atm_iv_observation(
        [
            {"underlyingKey": "NSE_INDEX|Nifty 50", "expiry": "2026-08-13", "strikePrice": 24900, "underlyingValue": 24962, "CE_impliedVolatility": 17, "PE_impliedVolatility": 19},
            {"underlyingKey": "NSE_INDEX|Nifty 50", "expiry": "2026-08-13", "strikePrice": 25000, "underlyingValue": 24962, "CE_impliedVolatility": 18, "PE_impliedVolatility": 20},
        ],
        data_date="2026-08-11",
        source_key="nse_option_chain_nifty",
    )
    provider = select_atm_iv_observation(
        [{"underlyingKey": "NSE_INDEX|Nifty 50", "expiry": "2026-08-13", "strikePrice": 25000, "underlyingSpotPrice": 24962, "CE_iv": 0.18, "PE_iv": 0.20}],
        data_date="2026-08-11",
        source_key="upstox_option_chain",
    )

    assert exchange["strikePrice"] == 25000
    assert exchange["atmIvPct"] == 19
    assert provider["atmIvPct"] == 19
    assert exchange["scoreEligible"] is False


def test_iv_rank_refuses_to_claim_252_sessions_early() -> None:
    result = calculate_iv_rank(
        [
            {"sourceKey": "upstox_option_chain", "underlyingKey": "NSE_INDEX|Nifty 50", "expiry": "2026-08-13", "dataDate": "2026-08-10", "atmIvPct": 18},
            {"sourceKey": "upstox_option_chain", "underlyingKey": "NSE_INDEX|Nifty 50", "expiry": "2026-08-13", "dataDate": "2026-08-11", "atmIvPct": 19},
        ],
        valid_trading_dates={"2026-08-10", "2026-08-11"},
    )

    assert result["state"] == "WAIT_INSUFFICIENT_HISTORY"
    assert result["sessionsAvailable"] == 2
    assert result["sessionsRequired"] == 252
    assert result["ivRankPct"] is None


def test_iv_rank_uses_exactly_latest_252_distinct_sessions() -> None:
    start = date(2025, 1, 1)
    sessions = []
    cursor = start
    while len(sessions) < 253:
        if cursor.weekday() < 5:
            sessions.append(cursor)
        cursor += timedelta(days=1)
    observations = [
        {
            "sourceKey": "upstox_option_chain",
            "underlyingKey": "NSE_INDEX|Nifty 50",
            "expiry": (session + timedelta(days=7)).isoformat(),
            "dataDate": session.isoformat(),
            "atmIvPct": 10 + index / 10,
        }
        for index, session in enumerate(sessions)
    ]
    observations.append({**observations[-1], "atmIvPct": 35.2})

    result = calculate_iv_rank(
        observations,
        valid_trading_dates={session.isoformat() for session in sessions},
    )

    assert result["state"] == "READY_INFORMATIONAL"
    assert result["sessionsAvailable"] == 253
    assert result["sessionsUsed"] == 252
    assert result["currentAtmIvPct"] == 35.2
    assert result["ivRankPct"] == 100
    assert result["scoreEligible"] is False


def test_iv_rank_rejects_fake_dates_weekends_and_mixed_underlyings() -> None:
    observations = [
        {
            "sourceKey": "upstox_option_chain",
            "underlyingKey": "NSE_INDEX|Nifty 50",
            "expiry": "2026-08-13",
            "dataDate": "fake-date",
            "atmIvPct": 18,
        },
        {
            "sourceKey": "upstox_option_chain",
            "underlyingKey": "NSE_INDEX|Nifty 50",
            "expiry": "2026-08-13",
            "dataDate": "2026-08-09",
            "atmIvPct": 18,
        },
        {
            "sourceKey": "upstox_option_chain",
            "underlyingKey": "NSE_INDEX|Nifty Bank",
            "expiry": "2026-08-13",
            "dataDate": "2026-08-10",
            "atmIvPct": 19,
        },
    ]

    result = calculate_iv_rank(
        observations,
        valid_trading_dates={"2026-08-10"},
        underlying_key="NSE_INDEX|Nifty 50",
    )

    assert result["state"] == "WAIT_INSUFFICIENT_HISTORY"
    assert result["sessionsAvailable"] == 0
    assert result["rejectedObservationCount"] == 3


def test_iv_rank_requires_official_session_set() -> None:
    result = calculate_iv_rank(
        [
            {
                "sourceKey": "upstox_option_chain",
                "underlyingKey": "NSE_INDEX|Nifty 50",
                "expiry": "2026-08-13",
                "dataDate": "2026-08-10",
                "atmIvPct": 18,
            }
        ]
    )

    assert result["state"] == "WAIT_CALENDAR_REQUIRED"
    assert result["ivRankPct"] is None
