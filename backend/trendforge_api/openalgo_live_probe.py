from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit

from .market_data_store import MarketDataStore
from .openalgo_client import (
    OPENALGO_READ_ONLY_ROUTES,
    OpenAlgoConfig,
    OpenAlgoDataClient,
    OpenAlgoUnavailable,
    Transport,
    openalgo_provider_contract,
)
from .openalgo_identity import (
    IdentityState,
    InstrumentIdentityQuery,
    InstrumentIdentityResult,
    OpenAlgoInstrumentMapper,
)
from .openalgo_replay import OpenAlgoReplayStore
from .openalgo_stream import OpenAlgoStreamManager, StreamContinuity


LIVE_PROBE_SCHEMA_VERSION = "trendforge.openalgo-live-probe.v1"
MAX_PROBE_INSTRUMENTS = 10
DEFAULT_MASTER_DB = Path(r"D:\openalgo\db\openalgo.db")
DEFAULT_WEBSOCKET_URL = "ws://127.0.0.1:8765"


class OpenAlgoLiveProbeBlocked(RuntimeError):
    """Fail-closed result for a bounded R17-G observation."""


class SyncWebSocket(Protocol):
    def send(self, payload: str) -> Any: ...

    def recv(self) -> str | bytes: ...

    def close(self) -> Any: ...


WebSocketFactory = Callable[[str, float], SyncWebSocket]


@dataclass(frozen=True)
class ProbeInstrument:
    exchange: str
    symbol: str

    def __post_init__(self) -> None:
        exchange = self.exchange.strip().upper()
        symbol = self.symbol.strip().upper()
        if exchange not in {"NSE", "NFO", "MCX"}:
            raise ValueError("probe exchange must be NSE, NFO, or MCX")
        if not symbol:
            raise ValueError("probe symbol cannot be empty")
        object.__setattr__(self, "exchange", exchange)
        object.__setattr__(self, "symbol", symbol)

    @property
    def key(self) -> tuple[str, str]:
        return self.exchange, self.symbol

    @classmethod
    def parse(cls, value: str) -> ProbeInstrument:
        exchange, separator, symbol = value.partition(":")
        if not separator:
            raise ValueError("instrument must use EXCHANGE:SYMBOL")
        return cls(exchange=exchange, symbol=symbol)

    def as_request(self) -> dict[str, str]:
        return {"exchange": self.exchange, "symbol": self.symbol}


@dataclass(frozen=True)
class LiveProbeRequest:
    universe: tuple[ProbeInstrument, ...]
    shortlist: tuple[ProbeInstrument, ...]
    websocket_url: str = DEFAULT_WEBSOCKET_URL
    quote_max_age_seconds: float = 120.0
    socket_timeout_seconds: float = 10.0
    history_interval: str = "D"
    history_lookback_days: int = 10

    def __post_init__(self) -> None:
        if not 1 <= len(self.universe) <= MAX_PROBE_INSTRUMENTS:
            raise ValueError("universe must contain one to ten instruments")
        if not self.shortlist:
            raise ValueError("shortlist cannot be empty")
        if len(self.shortlist) > MAX_PROBE_INSTRUMENTS:
            raise ValueError("shortlist cannot exceed ten instruments")
        if len({item.key for item in self.universe}) != len(self.universe):
            raise ValueError("universe instruments must be unique")
        if len({item.key for item in self.shortlist}) != len(self.shortlist):
            raise ValueError("shortlist instruments must be unique")
        universe_keys = {item.key for item in self.universe}
        if not {item.key for item in self.shortlist}.issubset(universe_keys):
            raise ValueError("shortlist must be a subset of the universe")
        if self.quote_max_age_seconds <= 0:
            raise ValueError("quote_max_age_seconds must be positive")
        if not 1 <= self.socket_timeout_seconds <= 60:
            raise ValueError("socket_timeout_seconds must be between 1 and 60")
        if not 1 <= self.history_lookback_days <= 366:
            raise ValueError("history_lookback_days must be between 1 and 366")
        _validate_local_websocket_url(self.websocket_url)


class RecordingTransport:
    """Record secret-free responses while delegating to the existing REST transport."""

    def __init__(self, delegate: Transport) -> None:
        self.delegate = delegate
        self._responses: dict[str, dict[str, Any]] = {}
        self.paths: list[str] = []

    def __call__(
        self, url: str, body: dict[str, Any], timeout: float
    ) -> dict[str, Any]:
        path = urlsplit(url).path
        if path not in OPENALGO_READ_ONLY_ROUTES:
            raise OpenAlgoUnavailable("live probe route is outside the read-only allowlist")
        response = self.delegate(url, body, timeout)
        if isinstance(response, dict):
            self._responses[path] = json.loads(
                json.dumps(response, ensure_ascii=True, allow_nan=False)
            )
        self.paths.append(path)
        return response

    def latest_bytes(self, path: str) -> bytes:
        response = self._responses.get(path)
        if response is None:
            raise OpenAlgoLiveProbeBlocked(f"no recorded response for {path}")
        return json.dumps(
            response,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")


@dataclass(frozen=True)
class LiveProbeDependencies:
    client: OpenAlgoDataClient
    recorder: RecordingTransport
    store: MarketDataStore
    websocket_factory: WebSocketFactory
    api_key: str


class OpenAlgoLiveObserver:
    """One bounded, operator-run R17-G observation with no activation side effect."""

    def __init__(
        self,
        dependencies: LiveProbeDependencies,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.dependencies = dependencies
        self.clock = clock
        if not dependencies.api_key:
            raise OpenAlgoLiveProbeBlocked("approved OpenAlgo API key is unavailable")

    def run(
        self,
        request: LiveProbeRequest,
        identities: Mapping[tuple[str, str], InstrumentIdentityResult],
    ) -> dict[str, Any]:
        observed_at = _aware_utc(self.clock())
        report = _base_report(observed_at, identities)
        try:
            ordered_universe = _require_identities(request.universe, identities)
            ordered_shortlist = _require_identities(request.shortlist, identities)
            rest_result = self._observe_rest(
                request=request,
                universe=ordered_universe,
                shortlist=ordered_shortlist,
                observed_at=observed_at,
            )
            report["rest"] = rest_result
            report["observationState"] = "REST_SHADOW_OBSERVED"

            stream_result = self._observe_stream(
                request=request,
                shortlist=ordered_shortlist,
                observed_at=observed_at,
            )
            report["stream"] = stream_result
            report["observationState"] = "STREAM_SHADOW_OBSERVED"
            report["status"] = "OBSERVED_WITH_CEILING"
        except Exception as exc:
            report["status"] = "BLOCKED"
            report["blockers"].append(_safe_error(exc, self.dependencies.api_key))
        report["blockers"] = sorted(set(report["blockers"]))
        return _assert_secret_free_report(report, self.dependencies.api_key)

    def _observe_rest(
        self,
        *,
        request: LiveProbeRequest,
        universe: tuple[InstrumentIdentityResult, ...],
        shortlist: tuple[InstrumentIdentityResult, ...],
        observed_at: datetime,
    ) -> dict[str, Any]:
        client = self.dependencies.client
        first = universe[0].contract
        assert first is not None
        client.ping()
        intervals = client.intervals()
        if request.history_interval not in {
            value for values in intervals.values() for value in values
        }:
            raise OpenAlgoLiveProbeBlocked("requested history interval is not advertised")

        first_quote = client.quote(
            symbol=first.symbol,
            exchange=first.exchange,
            max_age_seconds=request.quote_max_age_seconds,
            as_of=observed_at,
        )
        universe_rows = client.multiquote(
            symbols=[_identity_request(item) for item in universe],
            max_age_seconds=request.quote_max_age_seconds,
            as_of=observed_at,
        )
        shortlist_rows = client.multiquote(
            symbols=[_identity_request(item) for item in shortlist],
            max_age_seconds=request.quote_max_age_seconds,
            as_of=observed_at,
        )
        client.history(
            symbol=first.symbol,
            exchange=first.exchange,
            interval=request.history_interval,
            start_date=observed_at.date() - timedelta(days=request.history_lookback_days),
            end_date=observed_at.date(),
        )

        raw_quote = self.dependencies.recorder.latest_bytes("/api/v1/quotes")
        provider_contract = openalgo_provider_contract()
        replay = OpenAlgoReplayStore(
            self.dependencies.store,
            normalizer=_quote_normalizer(first.exchange, first.symbol),
            parser_version="trendforge.openalgo-quote.v1",
            provider_contract_hash=provider_contract.contract_hash,
        )
        capture = replay.capture_populated(
            route="/api/v1/quotes",
            identity=universe[0],
            raw_content=raw_quote,
            request_parameters={"exchange": first.exchange, "symbol": first.symbol},
            received_at=observed_at,
            trading_date=observed_at.date(),
            data_date=observed_at.date(),
            freshness_state="CURRENT_FOR_CONTRACT",
            run_id=f"r17-g-{observed_at.strftime('%Y%m%dT%H%M%SZ')}",
        )
        verification = replay.replay_latest(capture.source_key)
        if not verification.deterministic:
            raise OpenAlgoLiveProbeBlocked("OpenAlgo REST replay was not deterministic")
        return {
            "state": "REST_SHADOW_OBSERVED",
            "pingObserved": True,
            "intervalsObserved": True,
            "oneQuoteObserved": bool(first_quote),
            "universeQuoteCount": len(universe_rows),
            "shortlistQuoteCount": len(shortlist_rows),
            "historyObserved": True,
            "routes": tuple(self.dependencies.recorder.paths),
            "replay": {
                "sourceKey": capture.source_key,
                "rawContentHash": verification.raw_content_hash,
                "normalizedContentHash": verification.normalized_content_hash,
                "rowCount": verification.normalized_row_count,
                "deterministic": verification.deterministic,
            },
        }

    def _observe_stream(
        self,
        *,
        request: LiveProbeRequest,
        shortlist: tuple[InstrumentIdentityResult, ...],
        observed_at: datetime,
    ) -> dict[str, Any]:
        one_manager = OpenAlgoStreamManager(enabled=True, protocol_variant="SERVER")
        first_snapshot = self._socket_session(
            manager=one_manager,
            identities=(shortlist[0],),
            request=request,
            at=observed_at,
        )
        one_manager.stop()

        manager = OpenAlgoStreamManager(enabled=True, protocol_variant="SERVER")
        shortlist_snapshot = self._socket_session(
            manager=manager,
            identities=shortlist,
            request=request,
            at=_aware_utc(self.clock()),
        )
        manager.disconnect(reason_code="R17_G_PLANNED_RECONNECT")
        reconnect_snapshot = self._socket_session(
            manager=manager,
            identities=shortlist,
            request=request,
            at=_aware_utc(self.clock()),
        )
        final_snapshot = manager.snapshot(now=_aware_utc(self.clock()))
        manager.stop()
        if final_snapshot.continuity is not StreamContinuity.GAP_DETECTED:
            raise OpenAlgoLiveProbeBlocked(
                "planned reconnect did not retain explicit stream discontinuity"
            )
        return {
            "state": "STREAM_SHADOW_OBSERVED",
            "protocolVariant": "SERVER",
            "oneSymbolAccepted": first_snapshot.accepted_count,
            "shortlistAccepted": shortlist_snapshot.accepted_count,
            "reconnectAccepted": reconnect_snapshot.accepted_count,
            "connectionCount": final_snapshot.connection_count,
            "continuity": "STREAM_SEQUENCE_UNAVAILABLE",
            "providerSequenceAvailable": False,
            "evidenceEligible": False,
            "blockerCodes": tuple(sorted(final_snapshot.blocker_codes)),
        }

    def _socket_session(
        self,
        *,
        manager: OpenAlgoStreamManager,
        identities: tuple[InstrumentIdentityResult, ...],
        request: LiveProbeRequest,
        at: datetime,
    ):
        socket = self.dependencies.websocket_factory(
            request.websocket_url, request.socket_timeout_seconds
        )
        try:
            session_id = manager.begin_connect(at=at)
            socket.send(
                json.dumps(
                    {"action": "authenticate", "api_key": self.dependencies.api_key},
                    separators=(",", ":"),
                )
            )
            auth = _receive_type(socket, "auth")
            auth_ok = auth.get("status") == "success"
            manager.authentication_result(accepted=auth_ok, at=_aware_utc(self.clock()))
            if not auth_ok:
                raise OpenAlgoLiveProbeBlocked("OpenAlgo WebSocket authentication failed")

            subscription = manager.configure_subscriptions(
                evidence_shortlist=identities
            )
            if set(subscription) != {"action", "symbols", "mode", "type"}:
                raise OpenAlgoLiveProbeBlocked("OpenAlgo SERVER subscription contract drift")
            socket.send(json.dumps(subscription, separators=(",", ":")))
            acknowledgement = _receive_type(socket, "subscribe")
            accepted = _validate_subscription_ack(acknowledgement, identities)
            manager.subscription_result(
                accepted=accepted, at=_aware_utc(self.clock())
            )
            if not accepted:
                raise OpenAlgoLiveProbeBlocked(
                    "OpenAlgo WebSocket subscription was partial or invalid"
                )

            message = _receive_type(socket, "market_data")
            event_payload = _market_event_payload(message)
            event = manager.ingest(
                session_id=session_id,
                payload=event_payload,
                received_at=_aware_utc(self.clock()),
            )
            if event is None:
                raise OpenAlgoLiveProbeBlocked(
                    "OpenAlgo WebSocket event was not accepted"
                )
            return manager.snapshot(now=_aware_utc(self.clock()))
        finally:
            socket.close()


def load_exact_identities(
    master_db: Path,
    instruments: Sequence[ProbeInstrument],
    *,
    as_of: date,
) -> dict[tuple[str, str], InstrumentIdentityResult]:
    """Read only the requested OpenAlgo master rows through SQLite mode=ro."""

    resolved_path = master_db.expanduser().resolve()
    if not resolved_path.is_file():
        raise OpenAlgoLiveProbeBlocked("OpenAlgo master database is unavailable")
    uri = f"{resolved_path.as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows: list[dict[str, Any]] = []
        for instrument in instruments:
            matches = connection.execute(
                """
                SELECT symbol, brsymbol, name, exchange, brexchange, token,
                       expiry, strike, lotsize, instrumenttype, tick_size
                FROM symtoken
                WHERE UPPER(exchange) = ? AND UPPER(symbol) = ?
                ORDER BY id
                """,
                instrument.key,
            ).fetchall()
            rows.extend(dict(row) for row in matches)
    except sqlite3.Error as exc:
        raise OpenAlgoLiveProbeBlocked(
            f"OpenAlgo master database read failed: {type(exc).__name__}"
        ) from exc
    finally:
        connection.close()

    if not rows:
        raise OpenAlgoLiveProbeBlocked("OpenAlgo master returned no requested rows")
    source_version = _master_rows_version(rows)
    mapper = OpenAlgoInstrumentMapper.from_openalgo_master_rows(
        rows, source_version=source_version
    )
    results: dict[tuple[str, str], InstrumentIdentityResult] = {}
    for instrument in instruments:
        result = mapper.resolve(
            InstrumentIdentityQuery(
                exchange=instrument.exchange,
                symbol=instrument.symbol,
                as_of=as_of,
            )
        )
        if result.state is not IdentityState.EXACT:
            raise OpenAlgoLiveProbeBlocked(
                f"{instrument.exchange}:{instrument.symbol} {result.reason_code}"
            )
        results[instrument.key] = result
    return results


def default_websocket_factory(url: str, timeout: float) -> SyncWebSocket:
    _validate_local_websocket_url(url)
    try:
        import websocket
    except ImportError as exc:
        raise OpenAlgoLiveProbeBlocked(
            "websocket-client is unavailable; use the existing OpenAlgo environment"
        ) from exc
    return websocket.create_connection(url, timeout=timeout, enable_multithread=False)


def _require_identities(
    instruments: Sequence[ProbeInstrument],
    identities: Mapping[tuple[str, str], InstrumentIdentityResult],
) -> tuple[InstrumentIdentityResult, ...]:
    ordered: list[InstrumentIdentityResult] = []
    for instrument in instruments:
        result = identities.get(instrument.key)
        if (
            result is None
            or result.state is not IdentityState.EXACT
            or result.contract is None
        ):
            raise OpenAlgoLiveProbeBlocked(
                f"exact identity unavailable for {instrument.exchange}:{instrument.symbol}"
            )
        ordered.append(result)
    return tuple(ordered)


def _identity_request(identity: InstrumentIdentityResult) -> dict[str, str]:
    contract = identity.contract
    if identity.state is not IdentityState.EXACT or contract is None:
        raise OpenAlgoLiveProbeBlocked("exact identity is required")
    return {"exchange": contract.exchange, "symbol": contract.symbol}


def _quote_normalizer(exchange: str, symbol: str):
    def normalize(raw: bytes) -> tuple[dict[str, Any], ...]:
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict) or not data:
            return ()
        return (
            {
                "exchange": exchange,
                "symbol": symbol,
                "quote": data,
            },
        )

    return normalize


def _master_rows_version(rows: Sequence[Mapping[str, Any]]) -> str:
    canonical = json.dumps(
        [dict(row) for row in rows],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return f"symtoken-{hashlib.sha256(canonical).hexdigest()}"


def _receive_type(socket: SyncWebSocket, expected_type: str) -> dict[str, Any]:
    for _ in range(20):
        raw = socket.recv()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            message = json.loads(raw)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenAlgoLiveProbeBlocked(
                "OpenAlgo WebSocket returned malformed JSON"
            ) from exc
        if not isinstance(message, dict):
            raise OpenAlgoLiveProbeBlocked(
                "OpenAlgo WebSocket returned a non-object message"
            )
        if message.get("status") == "error":
            raise OpenAlgoLiveProbeBlocked(
                f"OpenAlgo WebSocket error: {message.get('code', 'UNKNOWN')}"
            )
        if message.get("type") == expected_type:
            return message
    raise OpenAlgoLiveProbeBlocked(
        f"OpenAlgo WebSocket did not produce {expected_type}"
    )


def _validate_subscription_ack(
    message: Mapping[str, Any],
    identities: Sequence[InstrumentIdentityResult],
) -> bool:
    if message.get("status") != "success":
        return False
    subscriptions = message.get("subscriptions")
    if not isinstance(subscriptions, list):
        return False
    expected = {
        (identity.contract.exchange, identity.contract.symbol)
        for identity in identities
        if identity.contract is not None
    }
    observed = {
        (
            str(item.get("exchange", "")).strip().upper(),
            str(item.get("symbol", "")).strip().upper(),
        )
        for item in subscriptions
        if isinstance(item, dict) and item.get("status") == "success"
    }
    return observed == expected and len(subscriptions) == len(expected)


def _market_event_payload(message: Mapping[str, Any]) -> dict[str, Any]:
    data = message.get("data")
    if not isinstance(data, dict):
        raise OpenAlgoLiveProbeBlocked(
            "OpenAlgo market-data event has no data object"
        )
    payload = dict(data)
    payload["exchange"] = str(message.get("exchange", "")).strip().upper()
    payload["symbol"] = str(message.get("symbol", "")).strip().upper()
    if "timestamp" not in payload and "timestamp" in message:
        payload["timestamp"] = message["timestamp"]
    return payload


def _base_report(
    observed_at: datetime,
    identities: Mapping[tuple[str, str], InstrumentIdentityResult],
) -> dict[str, Any]:
    hashes = sorted(
        {result.mapping_hash for result in identities.values() if result.mapping_hash}
    )
    return {
        "schemaVersion": LIVE_PROBE_SCHEMA_VERSION,
        "observedAt": observed_at.isoformat(),
        "status": "BLOCKED",
        "observationState": "FIXTURE_VERIFIED",
        "activationEligible": False,
        "continuity": "STREAM_SEQUENCE_UNAVAILABLE",
        "providerSequenceAvailable": False,
        "identity": {
            "count": len(identities),
            "mappingHashes": hashes,
            "instruments": [
                {"exchange": exchange, "symbol": symbol}
                for exchange, symbol in sorted(identities)
            ],
        },
        "rest": None,
        "stream": None,
        "blockers": ["STREAM_SEQUENCE_UNAVAILABLE"],
        "secretsIncluded": False,
        "executable": False,
    }


def _assert_secret_free_report(report: dict[str, Any], api_key: str) -> dict[str, Any]:
    serialized = json.dumps(report, ensure_ascii=True, allow_nan=False)
    forbidden = (
        "apikey",
        "api_key",
        "authorization",
        "access_token",
        "password",
        "cookie",
        "placeorder",
        "orderbook",
        "tradebook",
        "funds",
        "holdings",
        "positions",
    )
    if api_key and api_key in serialized:
        raise OpenAlgoLiveProbeBlocked("live report contained an API key")
    normalized = serialized.casefold()
    if any(term in normalized for term in forbidden):
        raise OpenAlgoLiveProbeBlocked("live report contained a forbidden field")
    return report


def _safe_error(exc: Exception, api_key: str) -> str:
    message = str(exc).replace(api_key, "[REDACTED]") if api_key else str(exc)
    return f"{type(exc).__name__}:{message[:400]}"


def _validate_local_websocket_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError("websocket URL must use ws or wss")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("R17-G WebSocket URL must remain loopback-only")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("websocket URL cannot contain credentials or query data")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("live observation timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _post_transport() -> Transport:
    from .openalgo_client import _post_json

    return _post_json


def _build_request(args: argparse.Namespace) -> LiveProbeRequest:
    universe = tuple(ProbeInstrument.parse(value) for value in args.instrument)
    shortlist_values = args.shortlist or args.instrument
    shortlist = tuple(ProbeInstrument.parse(value) for value in shortlist_values)
    return LiveProbeRequest(
        universe=universe,
        shortlist=shortlist,
        websocket_url=args.websocket_url,
        quote_max_age_seconds=args.quote_max_age_seconds,
        socket_timeout_seconds=args.socket_timeout_seconds,
        history_interval=args.history_interval,
        history_lookback_days=args.history_lookback_days,
    )


def _blocked_cli_report(exc: Exception, api_key: str = "") -> dict[str, Any]:
    return _assert_secret_free_report(
        {
            "schemaVersion": LIVE_PROBE_SCHEMA_VERSION,
            "status": "BLOCKED",
            "observationState": "FIXTURE_VERIFIED",
            "activationEligible": False,
            "continuity": "STREAM_SEQUENCE_UNAVAILABLE",
            "providerSequenceAvailable": False,
            "blockers": [_safe_error(exc, api_key)],
            "secretsIncluded": False,
            "executable": False,
        },
        api_key,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bounded read-only TrendForge R17-G OpenAlgo observer"
    )
    parser.add_argument(
        "--instrument",
        action="append",
        required=True,
        help="One to ten exact EXCHANGE:SYMBOL instruments",
    )
    parser.add_argument(
        "--shortlist",
        action="append",
        help="Subset of --instrument; defaults to the full bounded universe",
    )
    parser.add_argument(
        "--master-db", type=Path, default=DEFAULT_MASTER_DB
    )
    parser.add_argument(
        "--websocket-url", default=DEFAULT_WEBSOCKET_URL
    )
    parser.add_argument("--quote-max-age-seconds", type=float, default=120.0)
    parser.add_argument("--socket-timeout-seconds", type=float, default=10.0)
    parser.add_argument("--history-interval", default="D")
    parser.add_argument("--history-lookback-days", type=int, default=10)
    parser.add_argument(
        "--data-root", type=Path, default=Path(r"D:\TrendForge\data\market_data")
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path(r"D:\TrendForge\data\trendforge_research.db"),
    )
    args = parser.parse_args(argv)

    api_key = os.getenv("OPENALGO_API_KEY", "")
    try:
        request = _build_request(args)
        config = OpenAlgoConfig.from_env()
        recorder = RecordingTransport(_post_transport())
        dependencies = LiveProbeDependencies(
            client=OpenAlgoDataClient(config, transport=recorder),
            recorder=recorder,
            store=MarketDataStore(root=args.data_root, db_path=args.db_path),
            websocket_factory=default_websocket_factory,
            api_key=config.api_key,
        )
        all_instruments = tuple(
            dict.fromkeys((*request.universe, *request.shortlist))
        )
        identities = load_exact_identities(
            args.master_db, all_instruments, as_of=datetime.now(UTC).date()
        )
        report = OpenAlgoLiveObserver(dependencies).run(request, identities)
    except Exception as exc:
        report = _blocked_cli_report(exc, api_key)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "OBSERVED_WITH_CEILING" else 2


if __name__ == "__main__":
    raise SystemExit(main())