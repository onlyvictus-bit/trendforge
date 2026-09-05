from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from hashlib import sha256
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pydantic.alias_generators import to_camel


MAX_RESPONSE_BYTES = 25 * 1024 * 1024
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&._-]{1,80}$")
EXCHANGE_PATTERN = re.compile(r"^[A-Z0-9_]{2,20}$")
EXPIRY_TIME_PATTERN = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
OPTION_EXCHANGES = {"NFO", "BFO", "CDS", "MCX"}
OPENALGO_DERIVATIVES_ROUTE_STATUS = {
    "/api/v1/optionchain": "VERIFIED_READ_ONLY",
    "/api/v1/optiongreeks": "VERIFIED_READ_ONLY",
    "/api/v1/multioptiongreeks": "VERIFIED_READ_ONLY",
    "/api/v1/oi-analytics": "PROPOSED_NOT_EXPOSED",
    "/api/v1/gex": "PROPOSED_NOT_EXPOSED",
}
OPENALGO_READ_ONLY_ROUTES = (
    "/api/v1/ping",
    "/api/v1/intervals",
    "/api/v1/quotes",
    "/api/v1/multiquotes",
    "/api/v1/history",
    "/api/v1/optionchain",
    "/api/v1/optiongreeks",
    "/api/v1/multioptiongreeks",
)
OPENALGO_ROUTE_MIN_INTERVAL_SECONDS = {
    "/api/v1/ping": 0.1,
    "/api/v1/intervals": 0.1,
    "/api/v1/quotes": 0.1,
    "/api/v1/multiquotes": 0.1,
    "/api/v1/history": 0.35,
    "/api/v1/optionchain": 0.1,
    "/api/v1/optiongreeks": 0.1,
    "/api/v1/multioptiongreeks": 0.1,
}
OPENALGO_FORBIDDEN_ROUTE_TERMS = (
    "account",
    "cancelorder",
    "funds",
    "holdings",
    "margin",
    "modifyorder",
    "orderbook",
    "placeorder",
    "placesmartorder",
    "position",
    "tradebook",
)
OPENALGO_HISTORY_INTERVALS = {
    "1s",
    "5s",
    "10s",
    "15s",
    "30s",
    "45s",
    "1m",
    "2m",
    "3m",
    "5m",
    "10m",
    "15m",
    "20m",
    "30m",
    "60m",
    "1h",
    "2h",
    "3h",
    "4h",
    "D",
    "W",
    "M",
    "Q",
    "Y",
}
OPENALGO_PROVIDER_COMMIT = "24f8d395372799066a24ba1d6311f0e7791555d8"
OPENALGO_PROVIDER_CONTRACT_VERSION = "trendforge.openalgo-provider-contract.v1"
OPENALGO_PROVIDER_FILE_HASHES = {
    "restx_api/__init__.py": "24f7fd3e05546f32751afb1e7eefc0d047e29aa8960274f0266a0306b9f53cf1",
    "restx_api/ping.py": "107408043e72007ecc0c661fa5357f8b3401ab6a9521d7ca7fa02155950df85b",
    "restx_api/intervals.py": "5fad6b8820c6a2f58681302acd0c8f4e0584e031401b59602b5a821d5fedd46a",
    "restx_api/quotes.py": "6fddb10e07e75a1c415a8ae5830321df05b817bb72d33876bd9ddc228d22a633",
    "restx_api/multiquotes.py": "b9e74bf1c8858905dab80c49b1aba0009b61ddf3fc1f99ef252156a90e00f2f6",
    "restx_api/history.py": "81b7ac35e76777fe2818bc013700cbb99c6f12aa9daf54fe5c1c92cc2f86c856",
    "restx_api/option_chain.py": "49792505c0ba17ecdd84824cad63eb4a183470c9c37fbf3a7eabcb475b63051a",
    "restx_api/option_greeks.py": "38bf481661dbb47c95e3b9cba346aa5b5f97c827fd441d1ef48e308db61de2c3",
    "restx_api/multi_option_greeks.py": "6f34d91f5b2562a4a62ec5a55be3ff742520c4dff08c236c75b6e4481d822fc4",
    "websocket_proxy/server.py": "3b4192fc2669484e74ae00619b883c85d81459b87db1afb4fa8bcb823bad4ebd",
    "docs/api/websocket-streaming/quote.md": "aab3587d142fad1a46b04832bd2984921f590b4d541ffe1f0ccea4ec6202ee14",
}
OPENALGO_PROVIDER_ROUTE_SPECS = (
    {
        "path": "/api/v1/ping",
        "method": "POST",
        "purpose": "local service readiness and authentication check",
        "implementation_state": "CLIENT_IMPLEMENTED",
        "request_fields": ("apikey",),
        "response_fields": ("status", "data"),
    },
    {
        "path": "/api/v1/intervals",
        "method": "POST",
        "purpose": "broker-supported history intervals",
        "implementation_state": "CLIENT_IMPLEMENTED",
        "request_fields": ("apikey",),
        "response_fields": ("status", "data"),
    },
    {
        "path": "/api/v1/quotes",
        "method": "POST",
        "purpose": "single-instrument market snapshot",
        "implementation_state": "CLIENT_IMPLEMENTED",
        "request_fields": ("apikey", "symbol", "exchange"),
        "response_fields": ("status", "data"),
    },
    {
        "path": "/api/v1/multiquotes",
        "method": "POST",
        "purpose": "shortlist market snapshots",
        "implementation_state": "CLIENT_IMPLEMENTED",
        "request_fields": ("apikey", "symbols"),
        "response_fields": ("status", "results"),
    },
    {
        "path": "/api/v1/history",
        "method": "POST",
        "purpose": "closed historical candles",
        "implementation_state": "CLIENT_IMPLEMENTED",
        "request_fields": (
            "apikey",
            "symbol",
            "exchange",
            "interval",
            "start_date",
            "end_date",
        ),
        "response_fields": ("status", "data"),
    },
    {
        "path": "/api/v1/optionchain",
        "method": "POST",
        "purpose": "expiry-scoped option chain",
        "implementation_state": "CLIENT_IMPLEMENTED",
        "request_fields": (
            "apikey",
            "underlying",
            "exchange",
            "expiry_date",
            "strike_count",
        ),
        "response_fields": ("status", "chain"),
    },
    {
        "path": "/api/v1/optiongreeks",
        "method": "POST",
        "purpose": "single option-contract Greeks",
        "implementation_state": "CLIENT_IMPLEMENTED",
        "request_fields": ("apikey", "symbol", "exchange"),
        "response_fields": ("status", "greeks"),
    },
    {
        "path": "/api/v1/multioptiongreeks",
        "method": "POST",
        "purpose": "batch option-contract Greeks",
        "implementation_state": "CLIENT_IMPLEMENTED",
        "request_fields": ("apikey", "symbols"),
        "response_fields": ("status", "data", "summary"),
    },
)


class OpenAlgoUnavailable(RuntimeError):
    """Raised when the configured read-only OpenAlgo data boundary is unusable."""


class OpenAlgoTransientError(OpenAlgoUnavailable):
    """Retryable transport failure at the read-only OpenAlgo boundary."""


class OpenAlgoCapabilityState(StrEnum):
    """Observed readiness of the disabled-by-default OpenAlgo boundary."""

    ABSENT = "ABSENT"
    DISABLED = "DISABLED"
    FIXTURE_VERIFIED = "FIXTURE_VERIFIED"
    SHADOW_LIVE = "SHADOW_LIVE"
    REJECTED = "REJECTED"


class OpenAlgoCapabilityReport(BaseModel):
    """Secret-free Q5-R7 capability report; it never authorizes trading."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    milestone: str = "Q5-R7"
    acceptance_ceiling: str = "NO_INTRADAY_CONFIRMED"
    state: OpenAlgoCapabilityState
    enabled: bool
    configured: bool
    fixture_verified: bool
    live_shadow_verified: bool
    replay_integrity_passed: bool
    config_fingerprint: str | None = None
    advertised_read_only_routes: list[str] = Field(default_factory=list)
    forbidden_routes_present: list[str] = Field(default_factory=list)
    blocker_codes: list[str] = Field(default_factory=list)
    intraday_confirmation_allowed: bool = False
    account_access_allowed: bool = False
    executable: bool = False
    production_authorized: bool = False

    @model_validator(mode="after")
    def validate_boundary(self) -> "OpenAlgoCapabilityReport":
        if len(self.advertised_read_only_routes) != len(
            set(self.advertised_read_only_routes)
        ):
            raise ValueError("advertised OpenAlgo routes must be unique")
        if (
            self.forbidden_routes_present
            and self.state != OpenAlgoCapabilityState.REJECTED
        ):
            raise ValueError("forbidden routes require REJECTED capability state")
        if self.state == OpenAlgoCapabilityState.SHADOW_LIVE and not (
            self.enabled
            and self.configured
            and self.fixture_verified
            and self.live_shadow_verified
            and self.replay_integrity_passed
        ):
            raise ValueError(
                "SHADOW_LIVE requires configuration, fixture, live, and replay proof"
            )
        if self.state == OpenAlgoCapabilityState.REJECTED and not self.blocker_codes:
            raise ValueError("REJECTED capability state requires blocker codes")
        if (
            self.intraday_confirmation_allowed
            or self.account_access_allowed
            or self.executable
            or self.production_authorized
        ):
            raise ValueError(
                "Q5-R7 cannot authorize confirmation, account, or execution"
            )
        return self


class OpenAlgoRouteContractV1(BaseModel):
    """Pinned, secret-free description of one allowed provider route."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    path: str
    method: str
    purpose: str
    implementation_state: str
    request_fields: tuple[str, ...]
    response_fields: tuple[str, ...]

    @model_validator(mode="after")
    def validate_route(self) -> "OpenAlgoRouteContractV1":
        if not self.path.startswith("/api/v1/"):
            raise ValueError("OpenAlgo contract routes must stay under /api/v1/")
        if self.method != "POST":
            raise ValueError("OpenAlgo data contract routes must use POST")
        if len(self.request_fields) != len(set(self.request_fields)):
            raise ValueError("OpenAlgo request fields must be unique")
        if len(self.response_fields) != len(set(self.response_fields)):
            raise ValueError("OpenAlgo response fields must be unique")
        if "apikey" not in self.request_fields:
            raise ValueError("OpenAlgo route contract must declare apikey input")
        return self


class OpenAlgoProviderContractV1(BaseModel):
    """Machine-verifiable R17-B provider pin; it performs no broker I/O."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    schema_version: str = OPENALGO_PROVIDER_CONTRACT_VERSION
    provider: str = "OpenAlgo"
    provider_commit: str = OPENALGO_PROVIDER_COMMIT
    provider_file_hashes: dict[str, str] = Field(
        default_factory=lambda: dict(OPENALGO_PROVIDER_FILE_HASHES)
    )
    contract_hash: str
    routes: tuple[OpenAlgoRouteContractV1, ...]
    websocket_protocol_variants: tuple[str, ...] = (
        "DOCS:instruments|mode=quote|type=quote",
        "SERVER:symbols|mode=Quote|type=market_data",
    )
    provider_sequence_available: bool = False
    stream_continuity_state: str = "STREAM_SEQUENCE_UNAVAILABLE"
    secrets_included: bool = False
    executable: bool = False

    @model_validator(mode="after")
    def validate_contract(self) -> "OpenAlgoProviderContractV1":
        paths = [route.path for route in self.routes]
        if len(paths) != len(set(paths)):
            raise ValueError("OpenAlgo provider contract routes must be unique")
        forbidden = [path for path in paths if _route_is_forbidden(path)]
        if forbidden:
            raise ValueError("OpenAlgo provider contract contains forbidden routes")
        if not re.fullmatch(r"[0-9a-f]{40}", self.provider_commit):
            raise ValueError("OpenAlgo provider commit must be a full git SHA-1")
        if not self.provider_file_hashes or any(
            not path
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            for path, digest in self.provider_file_hashes.items()
        ):
            raise ValueError("OpenAlgo provider file hashes must be SHA-256")
        if not re.fullmatch(r"[0-9a-f]{64}", self.contract_hash):
            raise ValueError("OpenAlgo contract hash must be SHA-256")
        if self.provider_sequence_available:
            raise ValueError("provider sequence availability is not observed")
        if self.secrets_included or self.executable:
            raise ValueError("R17-B contract cannot include secrets or execution")
        return self


Transport = Callable[[str, dict[str, Any], float], dict[str, Any]]


@dataclass(frozen=True)
class OpenAlgoConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 15.0
    allow_remote: bool = False
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.25
    circuit_failure_threshold: int = 3
    circuit_cooldown_seconds: float = 30.0
    max_response_bytes: int = MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("OpenAlgo timeout_seconds must be positive")
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("OpenAlgo max_attempts must be between 1 and 5")
        if not 0 <= self.retry_backoff_seconds <= 10:
            raise ValueError("OpenAlgo retry_backoff_seconds must be between 0 and 10")
        if not 1 <= self.circuit_failure_threshold <= 10:
            raise ValueError(
                "OpenAlgo circuit_failure_threshold must be between 1 and 10"
            )
        if not 1 <= self.circuit_cooldown_seconds <= 300:
            raise ValueError(
                "OpenAlgo circuit_cooldown_seconds must be between 1 and 300"
            )
        if not 1 <= self.max_response_bytes <= MAX_RESPONSE_BYTES:
            raise ValueError(
                "OpenAlgo max_response_bytes must stay within the hard response limit"
            )

    @classmethod
    def from_env(cls) -> OpenAlgoConfig:
        if not _env_truthy(os.getenv("OPENALGO_ENABLED")):
            raise OpenAlgoUnavailable(
                "OpenAlgo is disabled by default; set OPENALGO_ENABLED=1 only for "
                "an approved read-only data session"
            )
        base_url = os.getenv("OPENALGO_BASE_URL", "").strip()
        api_key = os.getenv("OPENALGO_API_KEY", "").strip()
        allow_remote = _env_truthy(os.getenv("OPENALGO_ALLOW_REMOTE"))
        if not base_url or not api_key:
            raise OpenAlgoUnavailable(
                "OPENALGO_BASE_URL and OPENALGO_API_KEY are required for "
                "the enabled read-only data boundary"
            )
        return cls(base_url, api_key, allow_remote=allow_remote)


@dataclass
class _OpenAlgoRouteState:
    consecutive_failures: int = 0
    open_until: float = 0.0
    last_request_at: float | None = None


class OpenAlgoDataClient:
    """Read-only OpenAlgo market-data client; order routes are intentionally absent.

    PCR, Max Pain, beta, OI analytics, and GEX are TrendForge analytics. They are
    not silently inferred by this transport client. In particular, OpenAlgo's
    web-session OI/GEX pages are not equivalent to versioned API-key routes.
    """

    def __init__(
        self,
        config: OpenAlgoConfig,
        transport: Transport | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.config = config
        self.base_url = _validate_base_url(config.base_url, config.allow_remote)
        self._transport = transport or _post_json
        self._clock = clock
        self._sleep = sleeper
        self._route_states: dict[str, _OpenAlgoRouteState] = {}

    def ping(self) -> dict[str, str]:
        payload = self._request("/api/v1/ping", {})
        data = payload.get("data")
        if (
            not isinstance(data, dict)
            or str(data.get("message", "")).lower() != "pong"
            or not isinstance(data.get("broker"), str)
            or not data["broker"].strip()
        ):
            raise OpenAlgoUnavailable("OpenAlgo ping response failed schema validation")
        return {"message": "pong", "broker": data["broker"].strip()}

    def intervals(self) -> dict[str, list[str]]:
        payload = self._request("/api/v1/intervals", {})
        data = payload.get("data")
        categories = ("seconds", "minutes", "hours", "days", "weeks", "months")
        if not isinstance(data, dict) or any(
            not isinstance(data.get(category), list) for category in categories
        ):
            raise OpenAlgoUnavailable(
                "OpenAlgo intervals response failed schema validation"
            )
        normalized: dict[str, list[str]] = {}
        seen: set[str] = set()
        for category in categories:
            values = data[category]
            if any(
                not isinstance(value, str)
                or value not in OPENALGO_HISTORY_INTERVALS
                or value in seen
                for value in values
            ):
                raise OpenAlgoUnavailable(
                    "OpenAlgo intervals response contains invalid or duplicate tokens"
                )
            normalized[category] = list(values)
            seen.update(values)
        if not seen:
            raise OpenAlgoUnavailable("OpenAlgo intervals response has no usable intervals")
        return normalized

    def quote(
        self,
        *,
        symbol: str,
        exchange: str,
        max_age_seconds: float | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        _validate_symbol_exchange(symbol, exchange)
        if max_age_seconds is not None and max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        payload = self._request(
            "/api/v1/quotes",
            {"symbol": symbol.strip().upper(), "exchange": exchange.strip().upper()},
        )
        return _validate_quote_data(
            payload.get("data"), max_age_seconds=max_age_seconds, as_of=as_of
        )

    def multiquote(
        self,
        *,
        symbols: list[dict[str, str]],
        max_age_seconds: float | None = None,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if not 1 <= len(symbols) <= 100:
            raise ValueError("symbols must contain between 1 and 100 instruments")
        if max_age_seconds is not None and max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        normalized: list[dict[str, str]] = []
        requested_keys: list[tuple[str, str]] = []
        for item in symbols:
            if not isinstance(item, dict):
                raise ValueError("each multiquote instrument must be an object")
            symbol = str(item.get("symbol", "")).strip().upper()
            exchange = str(item.get("exchange", "")).strip().upper()
            _validate_symbol_exchange(symbol, exchange)
            key = (exchange, symbol)
            if key in requested_keys:
                raise ValueError("multiquote request instruments must be unique")
            requested_keys.append(key)
            normalized.append({"symbol": symbol, "exchange": exchange})

        payload = self._request("/api/v1/multiquotes", {"symbols": normalized})
        results = payload.get("results")
        if not isinstance(results, list) or len(results) != len(normalized):
            raise OpenAlgoUnavailable(
                "OpenAlgo multiquote response is partial or has no results array"
            )
        reconciled: dict[tuple[str, str], dict[str, Any]] = {}
        for result in results:
            if not isinstance(result, dict) or result.get("error"):
                raise OpenAlgoUnavailable(
                    "OpenAlgo multiquote response contains an error row"
                )
            symbol = str(result.get("symbol", "")).strip().upper()
            exchange = str(result.get("exchange", "")).strip().upper()
            key = (exchange, symbol)
            if key not in requested_keys or key in reconciled:
                raise OpenAlgoUnavailable(
                    "OpenAlgo multiquote response failed exact identity reconciliation"
                )
            reconciled[key] = {
                "symbol": symbol,
                "exchange": exchange,
                "data": _validate_quote_data(
                    result.get("data"),
                    max_age_seconds=max_age_seconds,
                    as_of=as_of,
                ),
            }
        if set(reconciled) != set(requested_keys):
            raise OpenAlgoUnavailable(
                "OpenAlgo multiquote response is missing requested instruments"
            )
        return [reconciled[key] for key in requested_keys]

    def history(
        self,
        *,
        symbol: str,
        exchange: str,
        interval: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        _validate_symbol_exchange(symbol, exchange)
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
        if interval not in OPENALGO_HISTORY_INTERVALS:
            raise ValueError(
                "interval must use an OpenAlgo interval token such as 1m, 4h, D, or W"
            )
        payload = self._request(
            "/api/v1/history",
            {
                "symbol": symbol.upper(),
                "exchange": exchange.upper(),
                "interval": interval,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise OpenAlgoUnavailable("OpenAlgo history response has no data array")
        if not rows:
            raise OpenAlgoUnavailable("OpenAlgo history response has no populated candles")
        normalized_rows: list[dict[str, Any]] = []
        previous_timestamp: datetime | None = None
        for row in rows:
            normalized_row, timestamp = _validate_history_row(row)
            if previous_timestamp is not None and timestamp <= previous_timestamp:
                raise OpenAlgoUnavailable(
                    "OpenAlgo history timestamps must be strictly increasing"
                )
            normalized_rows.append(normalized_row)
            previous_timestamp = timestamp
        return normalized_rows

    def option_chain(
        self,
        *,
        underlying: str,
        exchange: str,
        expiry_date: str,
        strike_count: int | None = None,
    ) -> dict[str, Any]:
        _validate_symbol_exchange(underlying, exchange)
        if not re.fullmatch(r"[0-3][0-9][A-Z]{3}[0-9]{2}", expiry_date.upper()):
            raise ValueError("expiry_date must use DDMMMYY format")
        if strike_count is not None and not 1 <= strike_count <= 100:
            raise ValueError("strike_count must be between 1 and 100")
        request_payload: dict[str, Any] = {
            "underlying": underlying.upper(),
            "exchange": exchange.upper(),
            "expiry_date": expiry_date.upper(),
        }
        if strike_count is not None:
            request_payload["strike_count"] = strike_count
        payload = self._request("/api/v1/optionchain", request_payload)
        if not isinstance(payload.get("chain"), list):
            raise OpenAlgoUnavailable(
                "OpenAlgo option-chain response has no chain array"
            )
        return payload

    def option_greeks(
        self,
        *,
        symbol: str,
        exchange: str,
        interest_rate: float | None = None,
        forward_price: float | None = None,
        underlying_symbol: str | None = None,
        underlying_exchange: str | None = None,
        expiry_time: str | None = None,
    ) -> dict[str, Any]:
        """Fetch Black-76 IV and Greeks for one option contract."""
        request_payload = _option_symbol_payload(
            symbol=symbol,
            exchange=exchange,
            underlying_symbol=underlying_symbol,
            underlying_exchange=underlying_exchange,
        )
        _add_greeks_parameters(
            request_payload,
            interest_rate=interest_rate,
            expiry_time=expiry_time,
        )
        if forward_price is not None:
            if forward_price < 0:
                raise ValueError("forward_price cannot be negative")
            request_payload["forward_price"] = forward_price

        payload = self._request("/api/v1/optiongreeks", request_payload)
        if not isinstance(payload.get("greeks"), dict):
            raise OpenAlgoUnavailable(
                "OpenAlgo option-greeks response has no greeks object"
            )
        return payload

    def multi_option_greeks(
        self,
        *,
        symbols: list[dict[str, str]],
        interest_rate: float | None = None,
        expiry_time: str | None = None,
    ) -> dict[str, Any]:
        """Fetch Black-76 IV and Greeks for at most 50 option contracts."""
        if not 1 <= len(symbols) <= 50:
            raise ValueError("symbols must contain between 1 and 50 contracts")

        normalized_symbols: list[dict[str, str]] = []
        for item in symbols:
            if not isinstance(item, dict):
                raise ValueError("each option contract must be an object")
            normalized_symbols.append(
                _option_symbol_payload(
                    symbol=str(item.get("symbol", "")),
                    exchange=str(item.get("exchange", "")),
                    underlying_symbol=item.get("underlying_symbol"),
                    underlying_exchange=item.get("underlying_exchange"),
                )
            )

        request_payload: dict[str, Any] = {"symbols": normalized_symbols}
        _add_greeks_parameters(
            request_payload,
            interest_rate=interest_rate,
            expiry_time=expiry_time,
        )
        payload = self._request("/api/v1/multioptiongreeks", request_payload)
        if not isinstance(payload.get("data"), list) or not isinstance(
            payload.get("summary"), dict
        ):
            raise OpenAlgoUnavailable(
                "OpenAlgo multi-option-greeks response failed schema validation"
            )
        return payload

    @staticmethod
    def derivatives_route_status() -> dict[str, str]:
        """Return explicit capability state without probing broker endpoints."""
        return dict(OPENALGO_DERIVATIVES_ROUTE_STATUS)

    def route_health(self, path: str) -> dict[str, Any]:
        """Return secret-free, per-route retry/circuit state."""
        if path not in OPENALGO_READ_ONLY_ROUTES:
            raise ValueError("unknown OpenAlgo read-only route")
        state = self._route_states.get(path, _OpenAlgoRouteState())
        now = self._clock()
        retry_after = max(0.0, state.open_until - now)
        return {
            "path": path,
            "state": "OPEN" if retry_after > 0 else "CLOSED",
            "consecutiveFailures": state.consecutive_failures,
            "retryAfterSeconds": retry_after,
        }

    def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if path not in OPENALGO_READ_ONLY_ROUTES or _route_is_forbidden(path):
            raise OpenAlgoUnavailable("OpenAlgo route is outside the read-only allowlist")
        route_state = self._route_states.setdefault(path, _OpenAlgoRouteState())
        now = self._clock()
        if route_state.open_until > now:
            raise OpenAlgoUnavailable(f"OpenAlgo route circuit is open for {path}")
        if route_state.open_until:
            route_state.open_until = 0.0
            route_state.consecutive_failures = 0

        body = {"apikey": self.config.api_key, **payload}
        for attempt in range(1, self.config.max_attempts + 1):
            self._enforce_route_budget(path, route_state)
            try:
                response = self._transport(
                    f"{self.base_url}{path}", body, self.config.timeout_seconds
                )
            except OpenAlgoTransientError as exc:
                route_state.consecutive_failures += 1
                if (
                    route_state.consecutive_failures
                    >= self.config.circuit_failure_threshold
                ):
                    route_state.open_until = (
                        self._clock() + self.config.circuit_cooldown_seconds
                    )
                    raise OpenAlgoUnavailable(
                        f"OpenAlgo route circuit is open for {path}"
                    ) from exc
                if attempt >= self.config.max_attempts:
                    raise OpenAlgoUnavailable(
                        _redact_openalgo_message(str(exc), self.config.api_key)
                    ) from exc
                self._sleep(self.config.retry_backoff_seconds * (2 ** (attempt - 1)))
                continue
            except Exception as exc:
                raise OpenAlgoUnavailable(
                    _redact_openalgo_message(
                        f"OpenAlgo request failed: {type(exc).__name__}: {exc}",
                        self.config.api_key,
                    )
                ) from exc

            _validate_response_size(response, self.config.max_response_bytes)
            if not isinstance(response, dict):
                raise OpenAlgoUnavailable("OpenAlgo returned a non-object response")
            if response.get("status") != "success":
                message = response.get("message") or response.get("error")
                raise OpenAlgoUnavailable(
                    _redact_openalgo_message(
                        str(message or "OpenAlgo request failed"), self.config.api_key
                    )
                )
            route_state.consecutive_failures = 0
            route_state.open_until = 0.0
            return response
        raise OpenAlgoUnavailable("OpenAlgo retry budget exhausted")

    def _enforce_route_budget(
        self, path: str, route_state: _OpenAlgoRouteState
    ) -> None:
        now = self._clock()
        minimum_interval = OPENALGO_ROUTE_MIN_INTERVAL_SECONDS[path]
        if route_state.last_request_at is not None:
            remaining = minimum_interval - (now - route_state.last_request_at)
            if remaining > 0:
                self._sleep(remaining)
        route_state.last_request_at = self._clock()


def parse_openalgo_history_timestamp(value: object) -> datetime:
    """Parse documented offset timestamps or explicit numeric JSON epochs."""
    if isinstance(value, bool):
        raise OpenAlgoUnavailable("OpenAlgo timestamp must not be boolean")
    if isinstance(value, (int, float)):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise OpenAlgoUnavailable("OpenAlgo timestamp must be finite")
        if abs(numeric) >= 100_000_000_000:
            numeric /= 1000.0
        try:
            return datetime.fromtimestamp(numeric, tz=timezone.utc)
        except (OSError, OverflowError, ValueError) as exc:
            raise OpenAlgoUnavailable("OpenAlgo numeric timestamp is out of range") from exc
    if not isinstance(value, str):
        raise OpenAlgoUnavailable(
            "OpenAlgo timestamp must be an offset string or numeric JSON value"
        )
    text = value.strip()
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        raise OpenAlgoUnavailable(
            "OpenAlgo epoch timestamp must use a numeric JSON value, not a string"
        )
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OpenAlgoUnavailable("OpenAlgo timestamp is not valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OpenAlgoUnavailable("OpenAlgo timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _validate_history_row(row: object) -> tuple[dict[str, Any], datetime]:
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not isinstance(row, dict) or not required.issubset(row):
        raise OpenAlgoUnavailable(
            "OpenAlgo history response failed candle schema validation"
        )
    timestamp = parse_openalgo_history_timestamp(row["timestamp"])
    open_price = _finite_number(row["open"], "open")
    high = _finite_number(row["high"], "high")
    low = _finite_number(row["low"], "low")
    close = _finite_number(row["close"], "close")
    volume = _finite_number(row["volume"], "volume")
    if min(open_price, high, low, close) <= 0:
        raise OpenAlgoUnavailable("OpenAlgo OHLC prices must be positive")
    if high < max(open_price, low, close) or low > min(open_price, high, close):
        raise OpenAlgoUnavailable("OpenAlgo history failed OHLC geometry validation")
    if volume < 0:
        raise OpenAlgoUnavailable("OpenAlgo history volume must be non-negative")
    normalized: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }
    if "oi" in row:
        oi = _finite_number(row["oi"], "oi")
        if oi < 0:
            raise OpenAlgoUnavailable("OpenAlgo history oi must be non-negative")
        normalized["oi"] = oi
    return normalized, timestamp


def _validate_quote_data(
    value: object,
    *,
    max_age_seconds: float | None,
    as_of: datetime | None,
) -> dict[str, Any]:
    required = {
        "open",
        "high",
        "low",
        "ltp",
        "ask",
        "bid",
        "prev_close",
        "volume",
    }
    if not isinstance(value, dict) or not required.issubset(value):
        raise OpenAlgoUnavailable("OpenAlgo quote data failed schema validation")
    normalized = {
        field: _finite_number(value[field], field)
        for field in sorted(required)
    }
    positive = ("open", "high", "low", "ltp", "prev_close")
    if any(normalized[field] <= 0 for field in positive):
        raise OpenAlgoUnavailable("OpenAlgo quote prices must be positive")
    if normalized["high"] < max(
        normalized["open"], normalized["low"], normalized["ltp"]
    ) or normalized["low"] > min(
        normalized["open"], normalized["high"], normalized["ltp"]
    ):
        raise OpenAlgoUnavailable("OpenAlgo quote failed OHLC geometry validation")
    if normalized["ask"] < 0 or normalized["bid"] < 0:
        raise OpenAlgoUnavailable("OpenAlgo quote bid/ask must be non-negative")
    if normalized["volume"] < 0:
        raise OpenAlgoUnavailable("OpenAlgo quote volume must be non-negative")
    if "oi" in value:
        normalized["oi"] = _finite_number(value["oi"], "oi")
        if normalized["oi"] < 0:
            raise OpenAlgoUnavailable("OpenAlgo quote oi must be non-negative")
    if "timestamp" in value:
        timestamp = parse_openalgo_history_timestamp(value["timestamp"])
        normalized["timestamp"] = timestamp.isoformat()
    elif max_age_seconds is not None:
        raise OpenAlgoUnavailable(
            "OpenAlgo quote has no timestamp for the requested freshness check"
        )
    if max_age_seconds is not None:
        reference = as_of or datetime.now(timezone.utc)
        if reference.tzinfo is None or reference.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        age_seconds = (reference.astimezone(timezone.utc) - timestamp).total_seconds()
        if age_seconds < 0 or age_seconds > max_age_seconds:
            raise OpenAlgoUnavailable("OpenAlgo quote is stale or future-dated")
    return normalized


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OpenAlgoUnavailable(f"OpenAlgo {field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise OpenAlgoUnavailable(f"OpenAlgo {field} must be finite")
    return number


def _validate_response_size(response: object, limit: int) -> None:
    try:
        raw = json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise OpenAlgoUnavailable("OpenAlgo response is not JSON serializable") from exc
    if len(raw) > limit:
        raise OpenAlgoUnavailable("OpenAlgo response exceeded the configured size limit")


def _redact_openalgo_message(message: str, api_key: str) -> str:
    redacted = message.replace(api_key, "[REDACTED]") if api_key else message
    return redacted[:1000]


def _env_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _route_is_forbidden(route: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", route.lower())
    return any(term in normalized for term in OPENALGO_FORBIDDEN_ROUTE_TERMS)


def openalgo_provider_contract() -> OpenAlgoProviderContractV1:
    """Return the pinned R17-B contract without contacting OpenAlgo."""

    routes = tuple(OpenAlgoRouteContractV1(**spec) for spec in OPENALGO_PROVIDER_ROUTE_SPECS)
    hash_payload = {
        "schema_version": OPENALGO_PROVIDER_CONTRACT_VERSION,
        "provider": "OpenAlgo",
        "provider_commit": OPENALGO_PROVIDER_COMMIT,
        "provider_file_hashes": OPENALGO_PROVIDER_FILE_HASHES,
        "routes": [
            route.model_dump(mode="json", by_alias=True) for route in routes
        ],
        "websocket_protocol_variants": [
            "DOCS:instruments|mode=quote|type=quote",
            "SERVER:symbols|mode=Quote|type=market_data",
        ],
        "provider_sequence_available": False,
        "stream_continuity_state": "STREAM_SEQUENCE_UNAVAILABLE",
    }
    contract_hash = sha256(
        json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return OpenAlgoProviderContractV1(contract_hash=contract_hash, routes=routes)


def assess_openalgo_capability(
    *,
    environment: Mapping[str, str] | None = None,
    fixture_verified: bool = True,
    live_shadow_verified: bool = False,
    replay_integrity_passed: bool = False,
    advertised_routes: tuple[str, ...] = OPENALGO_READ_ONLY_ROUTES,
) -> OpenAlgoCapabilityReport:
    """Classify the OpenAlgo boundary without contacting a broker or exposing secrets."""

    env = environment if environment is not None else os.environ
    enabled = _env_truthy(env.get("OPENALGO_ENABLED"))
    base_url = env.get("OPENALGO_BASE_URL", "").strip()
    api_key = env.get("OPENALGO_API_KEY", "").strip()
    allow_remote = _env_truthy(env.get("OPENALGO_ALLOW_REMOTE"))
    configured = bool(base_url and api_key)
    routes = list(advertised_routes)
    forbidden = sorted(route for route in routes if _route_is_forbidden(route))
    blockers: list[str] = []
    state: OpenAlgoCapabilityState

    if forbidden:
        state = OpenAlgoCapabilityState.REJECTED
        blockers.append("FORBIDDEN_EXECUTION_OR_ACCOUNT_ROUTE")
    elif not configured:
        state = OpenAlgoCapabilityState.ABSENT
        blockers.append("OPENALGO_CONFIGURATION_ABSENT")
    elif not enabled:
        state = OpenAlgoCapabilityState.DISABLED
        blockers.append("OPENALGO_DISABLED_BY_DEFAULT")
    else:
        try:
            _validate_base_url(base_url, allow_remote)
        except OpenAlgoUnavailable:
            state = OpenAlgoCapabilityState.REJECTED
            blockers.append("OPENALGO_UNSAFE_BASE_URL")
        else:
            if not fixture_verified:
                state = OpenAlgoCapabilityState.REJECTED
                blockers.append("OPENALGO_FIXTURE_CONTRACT_FAILED")
            elif live_shadow_verified and replay_integrity_passed:
                state = OpenAlgoCapabilityState.SHADOW_LIVE
                blockers.append("INTRADAY_CONFIRMATION_NOT_PROMOTED")
            else:
                state = OpenAlgoCapabilityState.FIXTURE_VERIFIED
                if not live_shadow_verified:
                    blockers.append("LIVE_SHADOW_NOT_VERIFIED")
                if not replay_integrity_passed:
                    blockers.append("REPLAY_INTEGRITY_NOT_VERIFIED")

    fingerprint = None
    if configured:
        fingerprint_payload = {
            "base_url": base_url,
            "api_key_present": True,
            "enabled": enabled,
            "allow_remote": allow_remote,
            "routes": routes,
        }
        fingerprint = sha256(
            json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

    return OpenAlgoCapabilityReport(
        state=state,
        enabled=enabled,
        configured=configured,
        fixture_verified=fixture_verified,
        live_shadow_verified=live_shadow_verified,
        replay_integrity_passed=replay_integrity_passed,
        config_fingerprint=fingerprint,
        advertised_read_only_routes=routes,
        forbidden_routes_present=forbidden,
        blocker_codes=blockers,
    )


def _validate_base_url(value: str, allow_remote: bool) -> str:
    parsed = urlparse(value.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise OpenAlgoUnavailable("OPENALGO_BASE_URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise OpenAlgoUnavailable(
            "OPENALGO_BASE_URL cannot contain credentials, query, or fragment"
        )
    if not allow_remote and parsed.hostname.lower() not in LOCAL_HOSTS:
        raise OpenAlgoUnavailable(
            "Remote OpenAlgo URLs are blocked unless OPENALGO_ALLOW_REMOTE=1"
        )
    return value.strip().rstrip("/")


def _validate_symbol_exchange(symbol: str, exchange: str) -> None:
    if not SYMBOL_PATTERN.fullmatch(symbol.strip().upper()):
        raise ValueError("invalid OpenAlgo symbol")
    if not EXCHANGE_PATTERN.fullmatch(exchange.strip().upper()):
        raise ValueError("invalid OpenAlgo exchange")


def _option_symbol_payload(
    *,
    symbol: str,
    exchange: str,
    underlying_symbol: str | None,
    underlying_exchange: str | None,
) -> dict[str, str]:
    _validate_symbol_exchange(symbol, exchange)
    normalized_exchange = exchange.strip().upper()
    if normalized_exchange not in OPTION_EXCHANGES:
        raise ValueError("option Greeks exchange must be one of NFO, BFO, CDS, or MCX")
    payload = {
        "symbol": symbol.strip().upper(),
        "exchange": normalized_exchange,
    }
    if underlying_symbol is not None:
        if not underlying_symbol.strip():
            raise ValueError("underlying_symbol cannot be empty")
        _validate_symbol_exchange(
            underlying_symbol,
            underlying_exchange or normalized_exchange,
        )
        payload["underlying_symbol"] = underlying_symbol.strip().upper()
    if underlying_exchange is not None:
        if underlying_symbol is None:
            raise ValueError("underlying_exchange requires an underlying_symbol")
        payload["underlying_exchange"] = underlying_exchange.strip().upper()
    return payload


def _add_greeks_parameters(
    payload: dict[str, Any],
    *,
    interest_rate: float | None,
    expiry_time: str | None,
) -> None:
    if interest_rate is not None:
        if not 0 <= interest_rate <= 100:
            raise ValueError("interest_rate must be between 0 and 100")
        payload["interest_rate"] = interest_rate
    if expiry_time is not None:
        if not EXPIRY_TIME_PATTERN.fullmatch(expiry_time):
            raise ValueError("expiry_time must use HH:MM 24-hour format")
        payload["expiry_time"] = expiry_time


def _post_json(
    url: str, payload: dict[str, Any], timeout_seconds: float
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code in {408, 425, 429, 500, 502, 503, 504}:
            raise OpenAlgoTransientError(
                f"OpenAlgo transient HTTP failure: {exc.code}"
            ) from exc
        raise OpenAlgoUnavailable(f"OpenAlgo HTTP failure: {exc.code}") from exc
    except (TimeoutError, URLError, OSError) as exc:
        raise OpenAlgoTransientError(
            f"OpenAlgo transient transport failure: {type(exc).__name__}"
        ) from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise OpenAlgoUnavailable(
            "OpenAlgo response exceeded the configured size limit"
        )
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OpenAlgoUnavailable("OpenAlgo returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise OpenAlgoUnavailable("OpenAlgo returned a non-object JSON response")
    return parsed
