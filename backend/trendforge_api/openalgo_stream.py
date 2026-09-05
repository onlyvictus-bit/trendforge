from __future__ import annotations

import hashlib
import json
from collections import deque
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .openalgo_client import parse_openalgo_history_timestamp
from .openalgo_identity import IdentityState, InstrumentIdentityResult


OPENALGO_STREAM_SCHEMA_VERSION = "trendforge.openalgo-stream.v1"


class OpenAlgoStreamTransport(Protocol):
    """Dependency-free boundary for a separately approved live transport."""

    def connect(self) -> None: ...

    def send(self, payload: dict[str, Any]) -> None: ...

    def close(self) -> None: ...


class StreamState(StrEnum):
    DISABLED = "DISABLED"
    DISCONNECTED = "DISCONNECTED"
    AUTHENTICATING = "AUTHENTICATING"
    CONNECTED = "CONNECTED"
    SUBSCRIBING = "SUBSCRIBING"
    ACTIVE = "ACTIVE"
    GAP_DETECTED = "GAP_DETECTED"
    RECONNECTING = "RECONNECTING"
    STOPPED = "STOPPED"


class StreamRole(StrEnum):
    EVIDENCE_SHORTLIST = "EVIDENCE_SHORTLIST"
    DISPLAY_ONLY = "DISPLAY_ONLY"


class StreamContinuity(StrEnum):
    STREAM_SEQUENCE_UNAVAILABLE = "STREAM_SEQUENCE_UNAVAILABLE"
    GAP_DETECTED = "GAP_DETECTED"


class ManagedStreamEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    local_receipt_sequence: int = Field(gt=0)
    exchange: str
    symbol: str
    provider_timestamp: datetime
    received_at: datetime
    role: StreamRole
    event_hash: str
    evidence_eligible: bool = False
    provider_sequence_available: bool = False


class StreamManagerSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = OPENALGO_STREAM_SCHEMA_VERSION
    state: StreamState
    continuity: StreamContinuity
    session_id: str | None
    connection_count: int = Field(ge=0)
    evidence_subscription_count: int = Field(ge=0)
    display_subscription_count: int = Field(ge=0)
    queue_size: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    duplicate_count: int = Field(ge=0)
    reordered_count: int = Field(ge=0)
    dropped_count: int = Field(ge=0)
    stale_session_count: int = Field(ge=0)
    heartbeat_age_seconds: float | None = Field(default=None, ge=0)
    blocker_codes: tuple[str, ...]
    provider_sequence_available: bool = False
    rest_fallback_repairs_gap: bool = False
    secrets_included: bool = False
    executable: bool = False


class OpenAlgoStreamManager:
    """R17-F stream integrity state machine; it opens no socket by itself."""

    def __init__(
        self,
        *,
        enabled: bool,
        protocol_variant: str = "DOCS",
        max_queue_size: int = 1_000,
        heartbeat_timeout_seconds: float = 30.0,
    ) -> None:
        if protocol_variant not in {"DOCS", "SERVER"}:
            raise ValueError("protocol_variant must be DOCS or SERVER")
        if not 1 <= max_queue_size <= 100_000:
            raise ValueError("max_queue_size must be between 1 and 100000")
        if not 1 <= heartbeat_timeout_seconds <= 300:
            raise ValueError("heartbeat timeout must be between 1 and 300 seconds")
        self.enabled = enabled
        self.protocol_variant = protocol_variant
        self.max_queue_size = max_queue_size
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.state = StreamState.DISCONNECTED if enabled else StreamState.DISABLED
        self.continuity = StreamContinuity.STREAM_SEQUENCE_UNAVAILABLE
        self._session_counter = 0
        self.session_id: str | None = None
        self.connection_count = 0
        self._evidence: dict[tuple[str, str], InstrumentIdentityResult] = {}
        self._display: dict[tuple[str, str], InstrumentIdentityResult] = {}
        self._queue: deque[ManagedStreamEvent] = deque()
        self._seen_hashes: set[str] = set()
        self._last_provider_timestamp: dict[tuple[str, str], datetime] = {}
        self._last_heartbeat_at: datetime | None = None
        self._local_sequence = 0
        self.accepted_count = 0
        self.duplicate_count = 0
        self.reordered_count = 0
        self.dropped_count = 0
        self.stale_session_count = 0
        self._blockers: set[str] = set()

    def begin_connect(self, *, at: datetime) -> str:
        self._require_aware(at)
        if not self.enabled:
            raise RuntimeError("OpenAlgo stream is disabled")
        if self.state not in {StreamState.DISCONNECTED, StreamState.RECONNECTING}:
            raise RuntimeError("one managed OpenAlgo connection already exists")
        self._session_counter += 1
        self.connection_count += 1
        self.session_id = f"openalgo-stream-{self._session_counter}"
        self.state = StreamState.AUTHENTICATING
        self._last_heartbeat_at = at.astimezone(UTC)
        return self.session_id

    def authentication_result(self, *, accepted: bool, at: datetime) -> None:
        self._require_aware(at)
        if self.state is not StreamState.AUTHENTICATING:
            raise RuntimeError("stream is not awaiting authentication")
        if not accepted:
            self.state = StreamState.DISCONNECTED
            self._blockers.add("WAIT_STREAM_AUTH")
            return
        self.state = StreamState.CONNECTED
        self._blockers.discard("WAIT_STREAM_AUTH")
        self._last_heartbeat_at = at.astimezone(UTC)

    def configure_subscriptions(
        self,
        *,
        evidence_shortlist: tuple[InstrumentIdentityResult, ...],
        display_only: tuple[InstrumentIdentityResult, ...] = (),
    ) -> dict[str, Any]:
        if self.state is not StreamState.CONNECTED:
            raise RuntimeError("stream must be connected before subscription")
        evidence = self._exact_identity_map(evidence_shortlist)
        display = self._exact_identity_map(display_only)
        for key in evidence:
            display.pop(key, None)
        if not evidence:
            raise ValueError("canonical evidence shortlist cannot be empty")
        if len(evidence) + len(display) > 100:
            raise ValueError("managed OpenAlgo stream is bounded to 100 instruments")
        self._evidence = evidence
        self._display = display
        self.state = StreamState.SUBSCRIBING
        instruments = [
            {"exchange": exchange, "symbol": symbol}
            for exchange, symbol in sorted((*evidence.keys(), *display.keys()))
        ]
        if self.protocol_variant == "DOCS":
            return {
                "action": "subscribe",
                "instruments": instruments,
                "mode": "quote",
                "type": "quote",
            }
        return {
            "action": "subscribe",
            "symbols": instruments,
            "mode": "Quote",
            "type": "market_data",
        }

    def subscription_result(self, *, accepted: bool, at: datetime) -> None:
        self._require_aware(at)
        if self.state is not StreamState.SUBSCRIBING:
            raise RuntimeError("stream is not awaiting subscription acknowledgement")
        if not accepted:
            self._mark_gap("WAIT_STREAM_SUBSCRIPTION")
            return
        self.state = StreamState.ACTIVE
        self._blockers.discard("WAIT_STREAM_SUBSCRIPTION")
        self._last_heartbeat_at = at.astimezone(UTC)

    def heartbeat(self, *, session_id: str, at: datetime) -> bool:
        self._require_aware(at)
        if session_id != self.session_id:
            self.stale_session_count += 1
            return False
        if self.state not in {StreamState.ACTIVE, StreamState.GAP_DETECTED}:
            return False
        self._last_heartbeat_at = at.astimezone(UTC)
        return True

    def check_heartbeat(self, *, now: datetime) -> bool:
        self._require_aware(now)
        if self.state not in {StreamState.ACTIVE, StreamState.GAP_DETECTED}:
            return False
        if self._last_heartbeat_at is None:
            self._mark_gap("WAIT_STREAM_HEARTBEAT")
            return False
        age = (now.astimezone(UTC) - self._last_heartbeat_at).total_seconds()
        if age > self.heartbeat_timeout_seconds:
            self._mark_gap("WAIT_STREAM_HEARTBEAT")
            return False
        return True

    def ingest(
        self,
        *,
        session_id: str,
        payload: dict[str, Any],
        received_at: datetime,
    ) -> ManagedStreamEvent | None:
        self._require_aware(received_at)
        if session_id != self.session_id:
            self.stale_session_count += 1
            return None
        if self.state not in {StreamState.ACTIVE, StreamState.GAP_DETECTED}:
            raise RuntimeError("stream is not active")
        exchange = str(payload.get("exchange", "")).strip().upper()
        symbol = str(payload.get("symbol", "")).strip().upper()
        key = (exchange, symbol)
        if key in self._evidence:
            role = StreamRole.EVIDENCE_SHORTLIST
        elif key in self._display:
            role = StreamRole.DISPLAY_ONLY
        else:
            self._mark_gap("WAIT_STREAM_UNSUBSCRIBED_EVENT")
            return None
        if "timestamp" not in payload:
            self._mark_gap("WAIT_STREAM_TIMESTAMP")
            return None
        provider_timestamp = parse_openalgo_history_timestamp(payload["timestamp"])
        event_hash = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        if event_hash in self._seen_hashes:
            self.duplicate_count += 1
            return None
        previous = self._last_provider_timestamp.get(key)
        if previous is not None and provider_timestamp <= previous:
            self.reordered_count += 1
            self._seen_hashes.add(event_hash)
            self._mark_gap("WAIT_STREAM_REORDER")
            return None
        if len(self._queue) >= self.max_queue_size:
            self.dropped_count += 1
            self._mark_gap("WAIT_STREAM_BACKPRESSURE")
            return None
        self._local_sequence += 1
        event = ManagedStreamEvent(
            session_id=session_id,
            local_receipt_sequence=self._local_sequence,
            exchange=exchange,
            symbol=symbol,
            provider_timestamp=provider_timestamp,
            received_at=received_at.astimezone(UTC),
            role=role,
            event_hash=event_hash,
            evidence_eligible=False,
            provider_sequence_available=False,
        )
        self._queue.append(event)
        self._seen_hashes.add(event_hash)
        self._last_provider_timestamp[key] = provider_timestamp
        self.accepted_count += 1
        return event

    def disconnect(self, *, reason_code: str) -> None:
        if self.state in {StreamState.DISABLED, StreamState.STOPPED}:
            return
        self._blockers.add(reason_code.strip() or "WAIT_STREAM_DISCONNECTED")
        self.continuity = StreamContinuity.GAP_DETECTED
        self.state = StreamState.RECONNECTING

    def record_rest_fallback(self) -> None:
        self._blockers.add("REST_FALLBACK_CANNOT_REPAIR_STREAM_GAP")

    def drain(self, *, limit: int | None = None) -> tuple[ManagedStreamEvent, ...]:
        count = len(self._queue) if limit is None else min(max(limit, 0), len(self._queue))
        return tuple(self._queue.popleft() for _ in range(count))

    def stop(self) -> None:
        self.state = StreamState.STOPPED
        self.session_id = None
        self._queue.clear()

    def snapshot(self, *, now: datetime | None = None) -> StreamManagerSnapshot:
        heartbeat_age: float | None = None
        if now is not None and self._last_heartbeat_at is not None:
            self._require_aware(now)
            heartbeat_age = max(
                0.0,
                (now.astimezone(UTC) - self._last_heartbeat_at).total_seconds(),
            )
        return StreamManagerSnapshot(
            state=self.state,
            continuity=self.continuity,
            session_id=self.session_id,
            connection_count=self.connection_count,
            evidence_subscription_count=len(self._evidence),
            display_subscription_count=len(self._display),
            queue_size=len(self._queue),
            accepted_count=self.accepted_count,
            duplicate_count=self.duplicate_count,
            reordered_count=self.reordered_count,
            dropped_count=self.dropped_count,
            stale_session_count=self.stale_session_count,
            heartbeat_age_seconds=heartbeat_age,
            blocker_codes=tuple(sorted(self._blockers)),
        )

    def _mark_gap(self, blocker: str) -> None:
        self._blockers.add(blocker)
        self.continuity = StreamContinuity.GAP_DETECTED
        self.state = StreamState.GAP_DETECTED

    @staticmethod
    def _exact_identity_map(
        identities: tuple[InstrumentIdentityResult, ...],
    ) -> dict[tuple[str, str], InstrumentIdentityResult]:
        result: dict[tuple[str, str], InstrumentIdentityResult] = {}
        for identity in identities:
            if identity.state is not IdentityState.EXACT or identity.contract is None:
                raise ValueError("stream subscription requires exact instrument identity")
            key = (identity.contract.exchange, identity.contract.symbol)
            if key in result:
                raise ValueError("stream subscription identities must be unique")
            result[key] = identity
        return result

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("stream timestamps must be timezone-aware")
