from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta

import pytest

from trendforge_api.market_data_store import MarketDataStore
from trendforge_api.openalgo_client import OpenAlgoConfig, OpenAlgoDataClient, OpenAlgoUnavailable
from trendforge_api.openalgo_identity import InstrumentIdentityQuery, OpenAlgoInstrumentMapper
from trendforge_api.openalgo_live_probe import (
    LiveProbeDependencies,
    LiveProbeRequest,
    OpenAlgoLiveObserver,
    OpenAlgoLiveProbeBlocked,
    ProbeInstrument,
    RecordingTransport,
    _assert_secret_free_report,
    _blocked_cli_report,
    load_exact_identities,
)


NOW = datetime(2026, 8, 31, 10, 0, tzinfo=UTC)
API_KEY = "r17-secret-key"


def _quote(timestamp: datetime = NOW):
    return {
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "ltp": 103.0,
        "ask": 103.1,
        "bid": 102.9,
        "prev_close": 100.0,
        "volume": 1000,
        "timestamp": timestamp.isoformat(),
    }


def _master_rows():
    return [
        {
            "exchange": "NSE",
            "symbol": "RELIANCE",
            "brsymbol": "RELIANCE-EQ",
            "name": "RELIANCE INDUSTRIES",
            "token": "2885",
            "expiry": None,
            "strike": None,
            "lotsize": 1,
            "instrumenttype": "EQ",
            "tick_size": 0.05,
        },
        {
            "exchange": "NSE",
            "symbol": "TCS",
            "brsymbol": "TCS-EQ",
            "name": "TATA CONSULTANCY SERVICES",
            "token": "11536",
            "expiry": None,
            "strike": None,
            "lotsize": 1,
            "instrumenttype": "EQ",
            "tick_size": 0.05,
        },
    ]


def _identities():
    mapper = OpenAlgoInstrumentMapper.from_openalgo_master_rows(
        _master_rows(), source_version="fixture-master"
    )
    return {
        ("NSE", symbol): mapper.resolve(
            InstrumentIdentityQuery(
                exchange="NSE", symbol=symbol, as_of=date(2026, 8, 31)
            )
        )
        for symbol in ("RELIANCE", "TCS")
    }


class FakeRestTransport:
    def __init__(self, *, partial: bool = False, error: str | None = None):
        self.partial = partial
        self.error = error
        self.calls = []

    def __call__(self, url, body, timeout):
        self.calls.append((url, dict(body), timeout))
        if self.error:
            raise RuntimeError(self.error)
        path = "/" + url.split("/", 3)[-1]
        if path == "/api/v1/ping":
            return {
                "status": "success",
                "data": {"message": "pong", "broker": "fixture"},
            }
        if path == "/api/v1/intervals":
            return {
                "status": "success",
                "data": {
                    "seconds": [],
                    "minutes": ["1m"],
                    "hours": [],
                    "days": ["D"],
                    "weeks": [],
                    "months": [],
                },
            }
        if path == "/api/v1/quotes":
            return {"status": "success", "data": _quote()}
        if path == "/api/v1/multiquotes":
            requested = body["symbols"]
            if self.partial:
                requested = requested[:1]
            return {
                "status": "success",
                "results": [
                    {
                        "symbol": item["symbol"],
                        "exchange": item["exchange"],
                        "data": _quote(),
                    }
                    for item in requested
                ],
            }
        if path == "/api/v1/history":
            return {
                "status": "success",
                "data": [
                    {
                        "timestamp": (NOW - timedelta(days=1)).isoformat(),
                        "open": 100.0,
                        "high": 105.0,
                        "low": 99.0,
                        "close": 103.0,
                        "volume": 1000,
                    },
                    {
                        "timestamp": NOW.isoformat(),
                        "open": 103.0,
                        "high": 106.0,
                        "low": 102.0,
                        "close": 104.0,
                        "volume": 1200,
                    },
                ],
            }
        raise AssertionError(f"unexpected route {path}")


class FakeSocket:
    def __init__(self, *, event_time: datetime, auth_ok=True, partial=False):
        self.event_time = event_time
        self.auth_ok = auth_ok
        self.partial = partial
        self.pending = []
        self.sent = []
        self.closed = False

    def send(self, payload):
        message = json.loads(payload)
        self.sent.append(message)
        if message["action"] == "authenticate":
            self.pending.append(
                {
                    "type": "auth",
                    "status": "success" if self.auth_ok else "error",
                    "code": "AUTH_FAILED" if not self.auth_ok else None,
                }
            )
            return
        assert message == {
            "action": "subscribe",
            "symbols": message["symbols"],
            "mode": "Quote",
            "type": "market_data",
        }
        subscriptions = [
            {**item, "status": "success", "mode": "Quote"}
            for item in message["symbols"]
        ]
        status = "success"
        if self.partial:
            subscriptions[-1]["status"] = "error"
            status = "partial"
        self.pending.extend(
            [
                {
                    "type": "subscribe",
                    "status": status,
                    "subscriptions": subscriptions,
                },
                {
                    "type": "market_data",
                    "exchange": message["symbols"][0]["exchange"],
                    "symbol": message["symbols"][0]["symbol"],
                    "data": {
                        "timestamp": self.event_time.isoformat(),
                        "ltp": 103.0,
                    },
                },
            ]
        )

    def recv(self):
        return json.dumps(self.pending.pop(0))

    def close(self):
        self.closed = True


class FakeSocketFactory:
    def __init__(self, **socket_options):
        self.socket_options = socket_options
        self.sockets = []

    def __call__(self, url, timeout):
        socket = FakeSocket(
            event_time=NOW + timedelta(seconds=len(self.sockets)),
            **self.socket_options,
        )
        self.sockets.append(socket)
        return socket


def _request():
    universe = (
        ProbeInstrument("NSE", "RELIANCE"),
        ProbeInstrument("NSE", "TCS"),
    )
    return LiveProbeRequest(
        universe=universe,
        shortlist=universe,
        quote_max_age_seconds=120,
    )


def _observer(tmp_path, transport=None, socket_factory=None):
    delegate = transport or FakeRestTransport()
    recorder = RecordingTransport(delegate)
    client = OpenAlgoDataClient(
        OpenAlgoConfig(
            "http://127.0.0.1:5000",
            API_KEY,
            max_attempts=1,
        ),
        transport=recorder,
        clock=lambda: 1.0,
        sleeper=lambda _: None,
    )
    sockets = socket_factory or FakeSocketFactory()
    dependencies = LiveProbeDependencies(
        client=client,
        recorder=recorder,
        store=MarketDataStore(
            root=tmp_path / "market-data", db_path=tmp_path / "market.db"
        ),
        websocket_factory=sockets,
        api_key=API_KEY,
    )
    return OpenAlgoLiveObserver(dependencies, clock=lambda: NOW), delegate, sockets


def test_r17_g_request_is_bounded_and_local_only():
    one = ProbeInstrument("NSE", "RELIANCE")
    with pytest.raises(ValueError, match="one to ten"):
        LiveProbeRequest(universe=tuple([one] * 11), shortlist=(one,))
    with pytest.raises(ValueError, match="loopback"):
        LiveProbeRequest(
            universe=(one,),
            shortlist=(one,),
            websocket_url="wss://broker.example/ws",
        )


def test_r17_g_shortlist_must_be_unique_subset():
    reliance = ProbeInstrument("NSE", "RELIANCE")
    tcs = ProbeInstrument("NSE", "TCS")
    with pytest.raises(ValueError, match="subset"):
        LiveProbeRequest(universe=(reliance,), shortlist=(tcs,))
    with pytest.raises(ValueError, match="unique"):
        LiveProbeRequest(
            universe=(reliance, tcs), shortlist=(reliance, reliance)
        )


def test_r17_g_master_database_is_read_only_and_exact(tmp_path):
    db_path = tmp_path / "openalgo.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE symtoken (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            brsymbol TEXT,
            name TEXT,
            exchange TEXT,
            brexchange TEXT,
            token TEXT,
            expiry TEXT,
            strike REAL,
            lotsize INTEGER,
            instrumenttype TEXT,
            tick_size REAL
        )
        """
    )
    for index, row in enumerate(_master_rows(), 1):
        connection.execute(
            """
            INSERT INTO symtoken VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                index,
                row["symbol"],
                row["brsymbol"],
                row["name"],
                row["exchange"],
                row.get("brexchange"),
                row["token"],
                row["expiry"],
                row["strike"],
                row["lotsize"],
                row["instrumenttype"],
                row["tick_size"],
            ),
        )
    connection.commit()
    connection.close()

    results = load_exact_identities(
        db_path,
        (ProbeInstrument("NSE", "RELIANCE"),),
        as_of=date(2026, 8, 31),
    )
    assert results[("NSE", "RELIANCE")].contract.token == "2885"
    assert sqlite3.connect(db_path).execute(
        "SELECT COUNT(*) FROM symtoken"
    ).fetchone()[0] == 2


def test_r17_g_unknown_or_ambiguous_master_identity_fails_closed(tmp_path):
    db_path = tmp_path / "empty.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE symtoken (
            id INTEGER PRIMARY KEY, symbol TEXT, brsymbol TEXT, name TEXT,
            exchange TEXT, brexchange TEXT, token TEXT, expiry TEXT,
            strike REAL, lotsize INTEGER, instrumenttype TEXT, tick_size REAL
        )
        """
    )
    connection.commit()
    connection.close()
    with pytest.raises(OpenAlgoLiveProbeBlocked, match="no requested rows"):
        load_exact_identities(
            db_path,
            (ProbeInstrument("NSE", "MISSING"),),
            as_of=date(2026, 8, 31),
        )


def test_r17_g_recording_transport_stores_no_request_or_secret():
    delegate = FakeRestTransport()
    recorder = RecordingTransport(delegate)
    response = recorder(
        "http://127.0.0.1:5000/api/v1/ping",
        {"apikey": API_KEY},
        1,
    )
    assert response["status"] == "success"
    assert API_KEY not in recorder.latest_bytes("/api/v1/ping").decode()
    assert not hasattr(recorder, "bodies")
    with pytest.raises(OpenAlgoUnavailable, match="allowlist"):
        recorder(
            "http://127.0.0.1:5000/api/v1/placeorder",
            {"apikey": API_KEY},
            1,
        )


def test_r17_g_full_sequence_observes_rest_stream_reconnect_and_replay(tmp_path):
    observer, delegate, sockets = _observer(tmp_path)
    report = observer.run(_request(), _identities())

    assert report["status"] == "OBSERVED_WITH_CEILING"
    assert report["observationState"] == "STREAM_SHADOW_OBSERVED"
    assert report["activationEligible"] is False
    assert report["providerSequenceAvailable"] is False
    assert report["continuity"] == "STREAM_SEQUENCE_UNAVAILABLE"
    assert report["rest"]["universeQuoteCount"] == 2
    assert report["rest"]["shortlistQuoteCount"] == 2
    assert report["rest"]["replay"]["deterministic"] is True
    assert report["stream"]["connectionCount"] == 2
    assert report["stream"]["reconnectAccepted"] == 2
    assert len(sockets.sockets) == 3
    assert all(socket.closed for socket in sockets.sockets)
    assert all(
        message.get("symbols") is not None
        and message.get("mode") == "Quote"
        for socket in sockets.sockets
        for message in socket.sent
        if message.get("action") == "subscribe"
    )
    paths = [call[0].split("127.0.0.1:5000")[-1] for call in delegate.calls]
    assert paths == [
        "/api/v1/ping",
        "/api/v1/intervals",
        "/api/v1/quotes",
        "/api/v1/multiquotes",
        "/api/v1/multiquotes",
        "/api/v1/history",
    ]
    assert all(set(call[1]) <= {"apikey", "symbol", "exchange", "symbols", "interval", "start_date", "end_date"} for call in delegate.calls)


def test_r17_g_partial_rest_fails_closed_before_stream(tmp_path):
    observer, _, sockets = _observer(
        tmp_path, transport=FakeRestTransport(partial=True)
    )
    report = observer.run(_request(), _identities())
    assert report["status"] == "BLOCKED"
    assert report["observationState"] == "FIXTURE_VERIFIED"
    assert sockets.sockets == []


def test_r17_g_socket_auth_failure_closes_socket_and_fails_closed(tmp_path):
    sockets = FakeSocketFactory(auth_ok=False)
    observer, _, _ = _observer(tmp_path, socket_factory=sockets)
    report = observer.run(_request(), _identities())
    assert report["status"] == "BLOCKED"
    assert report["observationState"] == "REST_SHADOW_OBSERVED"
    assert len(sockets.sockets) == 1
    assert sockets.sockets[0].closed is True


def test_r17_g_partial_subscription_closes_socket_and_fails_closed(tmp_path):
    sockets = FakeSocketFactory(partial=True)
    observer, _, _ = _observer(tmp_path, socket_factory=sockets)
    report = observer.run(_request(), _identities())
    assert report["status"] == "BLOCKED"
    assert sockets.sockets[0].closed is True


def test_r17_g_secret_is_redacted_from_blocked_report():
    report = _blocked_cli_report(RuntimeError(f"failed {API_KEY}"), API_KEY)
    serialized = json.dumps(report)
    assert API_KEY not in serialized
    assert "[REDACTED]" in serialized


def test_r17_g_report_rejects_forbidden_or_secret_fields():
    with pytest.raises(OpenAlgoLiveProbeBlocked, match="API key"):
        _assert_secret_free_report({"message": API_KEY}, API_KEY)
    with pytest.raises(OpenAlgoLiveProbeBlocked, match="forbidden"):
        _assert_secret_free_report({"orderbook": []}, API_KEY)