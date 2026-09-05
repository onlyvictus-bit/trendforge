from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .market_data_store import ManifestStatus, MarketDataStore, StoredAttempt
from .openalgo_client import OPENALGO_PROVIDER_COMMIT, OPENALGO_READ_ONLY_ROUTES
from .openalgo_identity import IdentityState, InstrumentIdentityResult


OPENALGO_REPLAY_SCHEMA_VERSION = "trendforge.openalgo-rest-replay.v1"
_SECRET_KEYS = frozenset(
    {"apikey", "api_key", "authorization", "access_token", "password", "secret", "cookie"}
)
_SOURCE_KEY_SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")

ReplayNormalizer = Callable[[bytes], Sequence[Mapping[str, Any]]]


class OpenAlgoReplayCapture(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: str
    attempt: StoredAttempt
    raw_content_hash: str | None = None
    normalized_content_hash: str | None = None
    last_good_hash: str | None = None
    replayable: bool = False


class OpenAlgoReplayVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: str
    raw_content_hash: str
    normalized_content_hash: str
    normalized_row_count: int = Field(gt=0)
    deterministic: bool
    parser_version: str
    identity_mapping_hash: str

    @model_validator(mode="after")
    def require_determinism(self) -> "OpenAlgoReplayVerification":
        if not self.deterministic:
            raise ValueError("replay output is not deterministic")
        return self


class OpenAlgoReplayStore:
    """R17-E adapter over the existing content-addressed MarketDataStore."""

    def __init__(
        self,
        store: MarketDataStore,
        *,
        normalizer: ReplayNormalizer,
        parser_version: str,
        provider_contract_hash: str,
    ) -> None:
        self.store = store
        self.normalizer = normalizer
        self.parser_version = parser_version.strip()
        self.provider_contract_hash = provider_contract_hash.casefold()
        if not self.parser_version:
            raise ValueError("parser_version cannot be empty")
        if not re.fullmatch(r"[0-9a-f]{64}", self.provider_contract_hash):
            raise ValueError("provider_contract_hash must be SHA-256")

    @staticmethod
    def source_key_for(route: str, identity: InstrumentIdentityResult) -> str:
        if identity.state is not IdentityState.EXACT or identity.contract is None:
            raise ValueError("OpenAlgo persistence requires exact instrument identity")
        route_name = route.removeprefix("/api/v1/").replace("/", "_")
        raw = f"openalgo_{route_name}_{identity.contract.exchange}_{identity.contract.symbol}"
        return _SOURCE_KEY_SAFE.sub("_", raw).strip("_").casefold()

    def capture_populated(
        self,
        *,
        route: str,
        identity: InstrumentIdentityResult,
        raw_content: bytes,
        request_parameters: Mapping[str, Any],
        received_at: datetime,
        trading_date: date,
        data_date: date | None,
        freshness_state: str,
        run_id: str,
        slot: str = "openalgo_rest",
        source_url: str = "openalgo://read-only",
        http_status: int = 200,
        retry_count: int = 0,
    ) -> OpenAlgoReplayCapture:
        self._validate_route_and_identity(route, identity)
        self._validate_secret_free(request_parameters, label="request parameters")
        self._validate_raw(raw_content)
        records = self._normalize(raw_content)
        if not records:
            raise ValueError("populated capture requires at least one normalized row")

        raw_ref = self.store.install_object(
            raw_content, extension="json", media_type="application/json"
        )
        normalized_payload = {"records": records}
        normalized_bytes = _canonical_bytes(normalized_payload)
        normalized_hash = hashlib.sha256(normalized_bytes).hexdigest()
        contract = identity.contract
        assert contract is not None
        previous = self.store.latest_for(self.source_key_for(route, identity))
        freshness = freshness_state.strip().upper()
        if not freshness:
            raise ValueError("freshness_state cannot be empty")
        envelope = {
            "schemaVersion": OPENALGO_REPLAY_SCHEMA_VERSION,
            "source": "OPENALGO",
            "route": route,
            "requestParameters": dict(request_parameters),
            "receivedAt": _aware_utc(received_at).isoformat(),
            "availabilityTimestamp": _aware_utc(received_at).isoformat(),
            "dataDate": data_date.isoformat() if data_date else None,
            "qualityState": "VALID_POPULATED",
            "freshnessState": freshness,
            "providerCommit": OPENALGO_PROVIDER_COMMIT,
            "providerContractHash": self.provider_contract_hash,
            "parserVersion": self.parser_version,
            "identityMappingVersion": identity.mapping_version,
            "identityMappingHash": identity.mapping_hash,
            "instrumentId": contract.canonical_id,
            "instrumentIdentity": {
                "exchange": contract.exchange,
                "segment": contract.segment,
                "symbol": contract.symbol,
                "token": contract.token,
                "instrumentType": contract.instrument_kind.value,
                "expiry": contract.expiry.isoformat() if contract.expiry else None,
                "strike": contract.strike,
                "optionType": contract.option_type,
                "lotSize": contract.lot_size,
                "tickSize": contract.tick_size,
                "unit": contract.unit,
                "validFrom": contract.valid_from.isoformat() if contract.valid_from else None,
                "validTo": contract.valid_to.isoformat() if contract.valid_to else None,
                "mappingSource": contract.mapping_source,
                "sourceVersion": contract.source_version,
            },
            "rawContentHash": raw_ref.content_hash,
            "payloadHash": raw_ref.content_hash,
            "normalizedContentHash": normalized_hash,
            "normalizedRecords": records,
            "previousLastGoodHash": previous.content_hash if previous else None,
        }
        envelope_bytes = _canonical_bytes(envelope)
        source_key = self.source_key_for(route, identity)
        self.store.commit_success(
            run_id=f"{run_id}-raw",
            source_key=f"{source_key}__raw",
            trading_date=trading_date,
            slot=slot,
            attempted_at=_aware_utc(received_at),
            fetched_at=_aware_utc(received_at),
            data_date=data_date,
            source_url=source_url,
            http_status=http_status,
            media_type="application/json",
            content=raw_content,
            extension="json",
            normalized_row_count=len(records),
            retry_count=retry_count,
        )
        attempt = self.store.commit_success(
            run_id=run_id,
            source_key=source_key,
            trading_date=trading_date,
            slot=slot,
            attempted_at=_aware_utc(received_at),
            fetched_at=_aware_utc(received_at),
            data_date=data_date,
            source_url=source_url,
            http_status=http_status,
            media_type="application/vnd.trendforge.openalgo-replay+json",
            content=envelope_bytes,
            extension="json",
            normalized_row_count=len(records),
            retry_count=retry_count,
        )
        return OpenAlgoReplayCapture(
            source_key=source_key,
            attempt=attempt,
            raw_content_hash=raw_ref.content_hash,
            normalized_content_hash=normalized_hash,
            last_good_hash=attempt.content_hash,
            replayable=True,
        )

    def capture_nonpublishable(
        self,
        *,
        route: str,
        identity: InstrumentIdentityResult,
        status: ManifestStatus,
        reason: str,
        received_at: datetime,
        trading_date: date,
        run_id: str,
        raw_content: bytes = b"",
        slot: str = "openalgo_rest",
        source_url: str = "openalgo://read-only",
        http_status: int | None = None,
        retry_count: int = 0,
    ) -> OpenAlgoReplayCapture:
        self._validate_route_and_identity(route, identity)
        if status not in {
            ManifestStatus.FAILED,
            ManifestStatus.PARTIAL,
            ManifestStatus.VALID_EMPTY,
            ManifestStatus.STALE_LAST_GOOD,
        }:
            raise ValueError("nonpublishable capture requires a fail-closed status")
        raw_hash: str | None = None
        if raw_content:
            self._validate_raw(raw_content, allow_empty_object=True)
            raw_ref = self.store.install_object(
                raw_content, extension="json", media_type="application/json"
            )
            raw_hash = raw_ref.content_hash
        source_key = self.source_key_for(route, identity)
        error = reason.strip() or "OpenAlgo response is not publishable"
        if raw_hash:
            error = f"{error}; rawContentHash={raw_hash}"
        attempt = self.store.record_attempt(
            run_id=run_id,
            source_key=source_key,
            trading_date=trading_date,
            slot=slot,
            attempted_at=_aware_utc(received_at),
            status=status,
            source_url=source_url,
            http_status=http_status,
            error=error,
            retry_count=retry_count,
        )
        latest = self.store.latest_for(source_key)
        return OpenAlgoReplayCapture(
            source_key=source_key,
            attempt=attempt,
            raw_content_hash=raw_hash,
            last_good_hash=latest.content_hash if latest else None,
            replayable=False,
        )

    def replay_latest(self, source_key: str) -> OpenAlgoReplayVerification:
        latest = self.store.latest_for(source_key)
        if latest is None or latest.content_hash is None:
            raise ValueError("no populated OpenAlgo last-good capture exists")
        envelope_bytes = self._read_verified_object(latest.content_hash)
        try:
            envelope = json.loads(envelope_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("stored OpenAlgo replay envelope is invalid JSON") from exc
        if not isinstance(envelope, dict) or envelope.get("schemaVersion") != OPENALGO_REPLAY_SCHEMA_VERSION:
            raise ValueError("stored OpenAlgo replay envelope has wrong schema")
        if envelope.get("parserVersion") != self.parser_version:
            raise ValueError("stored OpenAlgo replay parser version does not match")
        if envelope.get("providerContractHash") != self.provider_contract_hash:
            raise ValueError("stored OpenAlgo provider contract hash does not match")
        raw_hash = str(envelope.get("rawContentHash", "")).casefold()
        expected_hash = str(envelope.get("normalizedContentHash", "")).casefold()
        if not re.fullmatch(r"[0-9a-f]{64}", raw_hash) or not re.fullmatch(
            r"[0-9a-f]{64}", expected_hash
        ):
            raise ValueError("stored OpenAlgo replay hashes are invalid")
        raw_content = self._read_verified_object(raw_hash)
        records = self._normalize(raw_content)
        actual_hash = hashlib.sha256(_canonical_bytes({"records": records})).hexdigest()
        if actual_hash != expected_hash or records != envelope.get("normalizedRecords"):
            raise ValueError("OpenAlgo deterministic replay hash mismatch")
        if not records:
            raise ValueError("OpenAlgo replay produced no populated records")
        return OpenAlgoReplayVerification(
            source_key=source_key,
            raw_content_hash=raw_hash,
            normalized_content_hash=actual_hash,
            normalized_row_count=len(records),
            deterministic=True,
            parser_version=self.parser_version,
            identity_mapping_hash=str(envelope.get("identityMappingHash", "")),
        )

    def _normalize(self, raw_content: bytes) -> list[dict[str, Any]]:
        try:
            rows = self.normalizer(raw_content)
        except Exception as exc:
            raise ValueError(f"OpenAlgo normalization failed: {type(exc).__name__}") from exc
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError("OpenAlgo normalizer emitted a non-object row")
            normalized.append(dict(row))
        self._validate_secret_free(normalized, label="normalized records")
        return json.loads(_canonical_bytes(normalized))

    def _read_verified_object(self, content_hash: str) -> bytes:
        path: Path = self.store.object_path_for_hash(content_hash)
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != content_hash:
            raise ValueError("stored OpenAlgo content hash mismatch")
        return payload

    @staticmethod
    def _validate_route_and_identity(
        route: str, identity: InstrumentIdentityResult
    ) -> None:
        if route not in OPENALGO_READ_ONLY_ROUTES:
            raise ValueError("OpenAlgo replay route is outside the read-only allowlist")
        if identity.state is not IdentityState.EXACT or identity.contract is None:
            raise ValueError("OpenAlgo replay requires exact instrument identity")

    @staticmethod
    def _validate_raw(raw_content: bytes, *, allow_empty_object: bool = False) -> None:
        if not raw_content:
            raise ValueError("OpenAlgo raw capture cannot be empty")
        try:
            payload = json.loads(raw_content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("OpenAlgo raw capture must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("OpenAlgo raw capture must be a JSON object")
        if not allow_empty_object and not payload:
            raise ValueError("OpenAlgo HTTP 200 empty object is not usable data")
        OpenAlgoReplayStore._validate_secret_free(payload, label="raw response")

    @staticmethod
    def _validate_secret_free(value: Any, *, label: str) -> None:
        if _contains_secret_key(value):
            raise ValueError(f"{label} contains a credential field")


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).strip().casefold() in _SECRET_KEYS:
                return True
            if _contains_secret_key(nested):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_secret_key(item) for item in value)
    return False


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("OpenAlgo capture timestamp must be timezone-aware")
    return value.astimezone(UTC)
