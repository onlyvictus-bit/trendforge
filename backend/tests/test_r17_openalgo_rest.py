from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from trendforge_api.openalgo_client import (
    OpenAlgoConfig,
    OpenAlgoDataClient,
    OpenAlgoTransientError,
    OpenAlgoUnavailable,
    parse_openalgo_history_timestamp,
)


def _history_row(timestamp: object = "2025-04-01 09:15:00+05:30") -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "open": 766.5,
        "high": 774.0,
        "low": 763.2,
        "close": 772.5,
        "volume": 318625,
        "oi": 1200,
    }


def _quote_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "open": 1172.0,
        "high": 1196.6,
        "low": 1163.3,
        "ltp": 1187.75,
        "ask": 1188.0,
        "bid": 1187.85,
        "prev_close": 1165.7,
        "volume": 14414545,
    }
    data.update(overrides)
    return data


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


def test_documented_ist_history_timestamp_normalizes_to_utc() -> None:
    parsed = parse_openalgo_history_timestamp("2025-04-01 09:15:00+05:30")

    assert parsed.isoformat() == "2025-04-01T03:45:00+00:00"


def test_numeric_epoch_requires_numeric_json_type() -> None:
    parsed = parse_openalgo_history_timestamp(1743488100)

    assert parsed.tzinfo is timezone.utc
    with pytest.raises(OpenAlgoUnavailable, match="numeric JSON value"):
        parse_openalgo_history_timestamp("1743488100")
    with pytest.raises(OpenAlgoUnavailable, match="timezone-aware"):
        parse_openalgo_history_timestamp("2025-04-01 09:15:00")


def test_history_normalizes_and_validates_populated_candles() -> None:
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"),
        lambda *_: {"status": "success", "data": [_history_row()]},
    )

    rows = client.history(
        symbol="SBIN",
        exchange="NSE",
        interval="5m",
        start_date=date(2025, 4, 1),
        end_date=date(2025, 4, 8),
    )

    assert rows == [
        {
            "timestamp": "2025-04-01T03:45:00+00:00",
            "open": 766.5,
            "high": 774.0,
            "low": 763.2,
            "close": 772.5,
            "volume": 318625.0,
            "oi": 1200.0,
        }
    ]


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([], "no populated candles"),
        ([_history_row("2025-04-01 09:15:00")], "timezone-aware"),
        ([{**_history_row(), "close": 800}], "OHLC geometry"),
        ([{**_history_row(), "volume": -1}], "volume"),
        ([{**_history_row(), "open": float("nan")}], "finite"),
        (
            [_history_row(), _history_row("2025-04-01 09:15:00+05:30")],
            "strictly increasing",
        ),
        (
            [
                _history_row("2025-04-01 09:20:00+05:30"),
                _history_row("2025-04-01 09:15:00+05:30"),
            ],
            "strictly increasing",
        ),
    ],
)
def test_history_fails_closed_on_unusable_rows(
    rows: list[dict[str, object]], message: str
) -> None:
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"),
        lambda *_: {"status": "success", "data": rows},
    )

    with pytest.raises(OpenAlgoUnavailable, match=message):
        client.history(
            symbol="SBIN",
            exchange="NSE",
            interval="5m",
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 8),
        )


def test_ping_and_intervals_validate_provider_shapes() -> None:
    responses = {
        "/api/v1/ping": {
            "status": "success",
            "data": {"message": "pong", "broker": "fivepaisa"},
        },
        "/api/v1/intervals": {
            "status": "success",
            "data": {
                "months": [],
                "weeks": [],
                "days": ["D"],
                "hours": ["1h"],
                "minutes": ["1m", "5m", "60m"],
                "seconds": [],
            },
        },
    }

    def transport(url, _body, _timeout):
        return responses[url.removeprefix("http://127.0.0.1:5000")]

    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"), transport
    )

    assert client.ping() == {"message": "pong", "broker": "fivepaisa"}
    assert client.intervals()["minutes"] == ["1m", "5m", "60m"]


def test_quote_validates_numeric_fields_and_optional_freshness() -> None:
    now = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)
    payload = {
        "status": "success",
        "data": _quote_data(timestamp=(now - timedelta(seconds=2)).isoformat()),
    }
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"), lambda *_: payload
    )

    quote = client.quote(
        symbol="RELIANCE",
        exchange="NSE",
        max_age_seconds=5,
        as_of=now,
    )

    assert quote["ltp"] == 1187.75


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({}, "quote data"),
        (_quote_data(ltp="bad"), "numeric"),
        (_quote_data(ltp=1300), "OHLC geometry"),
        (_quote_data(volume=-1), "volume"),
    ],
)
def test_quote_fails_closed_on_bad_payload(
    data: dict[str, object], message: str
) -> None:
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"),
        lambda *_: {"status": "success", "data": data},
    )

    with pytest.raises(OpenAlgoUnavailable, match=message):
        client.quote(symbol="RELIANCE", exchange="NSE")


def test_quote_rejects_stale_or_timestamp_missing_when_age_is_required() -> None:
    now = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)
    stale = {
        "status": "success",
        "data": _quote_data(timestamp=(now - timedelta(seconds=30)).isoformat()),
    }
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"), lambda *_: stale
    )

    with pytest.raises(OpenAlgoUnavailable, match="stale"):
        client.quote(
            symbol="RELIANCE", exchange="NSE", max_age_seconds=5, as_of=now
        )

    missing = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"),
        lambda *_: {"status": "success", "data": _quote_data()},
    )
    with pytest.raises(OpenAlgoUnavailable, match="has no timestamp"):
        missing.quote(
            symbol="RELIANCE", exchange="NSE", max_age_seconds=5, as_of=now
        )


def test_multiquote_requires_exact_complete_identity_reconciliation() -> None:
    requested = [
        {"symbol": "RELIANCE", "exchange": "NSE"},
        {"symbol": "NIFTY30JAN25FUT", "exchange": "NFO"},
    ]
    payload = {
        "status": "success",
        "results": [
            {"symbol": item["symbol"], "exchange": item["exchange"], "data": _quote_data()}
            for item in requested
        ],
    }
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"), lambda *_: payload
    )

    rows = client.multiquote(symbols=requested)

    assert [row["symbol"] for row in rows] == ["RELIANCE", "NIFTY30JAN25FUT"]


@pytest.mark.parametrize(
    "results",
    [
        [{"symbol": "RELIANCE", "exchange": "NSE", "data": _quote_data()}],
        [
            {"symbol": "WRONG", "exchange": "NSE", "data": _quote_data()},
            {"symbol": "NIFTY30JAN25FUT", "exchange": "NFO", "data": _quote_data()},
        ],
        [
            {"symbol": "RELIANCE", "exchange": "NSE", "error": "not found"},
            {"symbol": "NIFTY30JAN25FUT", "exchange": "NFO", "data": _quote_data()},
        ],
    ],
)
def test_multiquote_partial_wrong_or_error_rows_fail_closed(
    results: list[dict[str, object]],
) -> None:
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"),
        lambda *_: {"status": "success", "results": results},
    )

    with pytest.raises(OpenAlgoUnavailable, match="multiquote"):
        client.multiquote(
            symbols=[
                {"symbol": "RELIANCE", "exchange": "NSE"},
                {"symbol": "NIFTY30JAN25FUT", "exchange": "NFO"},
            ]
        )


def test_transient_failures_retry_with_bound_and_then_close_circuit() -> None:
    calls = 0
    clock = FakeClock()

    def transport(_url, _body, _timeout):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise OpenAlgoTransientError("temporary timeout")
        return {"status": "success", "data": _quote_data()}

    client = OpenAlgoDataClient(
        OpenAlgoConfig(
            "http://127.0.0.1:5000",
            "secret",
            max_attempts=3,
            circuit_failure_threshold=4,
        ),
        transport,
        clock=clock,
        sleeper=clock.sleep,
    )

    assert client.quote(symbol="RELIANCE", exchange="NSE")["ltp"] == 1187.75
    assert calls == 3
    assert client.route_health("/api/v1/quotes")["state"] == "CLOSED"


def test_circuit_opens_per_route_after_repeated_transient_failure() -> None:
    calls = 0
    clock = FakeClock()

    def transport(_url, _body, _timeout):
        nonlocal calls
        calls += 1
        raise OpenAlgoTransientError("rate limited")

    client = OpenAlgoDataClient(
        OpenAlgoConfig(
            "http://127.0.0.1:5000",
            "secret",
            max_attempts=3,
            circuit_failure_threshold=2,
            circuit_cooldown_seconds=30,
        ),
        transport,
        clock=clock,
        sleeper=clock.sleep,
    )

    with pytest.raises(OpenAlgoUnavailable, match="circuit is open"):
        client.quote(symbol="RELIANCE", exchange="NSE")
    assert calls == 2
    assert client.route_health("/api/v1/quotes")["state"] == "OPEN"
    with pytest.raises(OpenAlgoUnavailable, match="circuit is open"):
        client.quote(symbol="RELIANCE", exchange="NSE")
    assert calls == 2


def test_route_rate_budget_is_applied_only_within_same_route() -> None:
    clock = FakeClock()
    client = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", "secret"),
        lambda *_: {"status": "success", "data": _quote_data()},
        clock=clock,
        sleeper=clock.sleep,
    )

    client.quote(symbol="RELIANCE", exchange="NSE")
    client.quote(symbol="TCS", exchange="NSE")

    assert clock.sleeps == [pytest.approx(0.1)]


def test_response_limit_and_secret_redaction_fail_closed() -> None:
    secret = "never-print-this-key"
    oversized = OpenAlgoDataClient(
        OpenAlgoConfig(
            "http://127.0.0.1:5000", secret, max_response_bytes=100
        ),
        lambda *_: {"status": "success", "data": {"value": "x" * 200}},
    )
    with pytest.raises(OpenAlgoUnavailable, match="size limit"):
        oversized.ping()

    leaking = OpenAlgoDataClient(
        OpenAlgoConfig("http://127.0.0.1:5000", secret),
        lambda *_: {"status": "error", "message": f"bad key {secret}"},
    )
    with pytest.raises(OpenAlgoUnavailable) as exc_info:
        leaking.ping()
    assert secret not in str(exc_info.value)
    assert "REDACTED" in str(exc_info.value)
