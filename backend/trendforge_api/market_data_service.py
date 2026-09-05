from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from .market_data_registry import (
    AcquisitionOwner,
    FetchGroupMode,
    MarketDataSourceContract,
)
from .market_data_store import ManifestStatus, MarketDataStore

# Sources where published "as-of / effective" dates can legitimately be ahead of
# the trading calendar day (next-session ban lists, option expiry stamps in JSON).
# Rows are still published; dataDate is clamped to trading_date for store safety.
_FUTURE_EFFECTIVE_DATE_KEYS = frozenset(
    {
        "nse_fno_ban",
        "nse_option_chain_nifty",
        "nse_option_chain_banknifty",
        "nse_index_option_chain_v3",
    }
)
_FUTURE_EFFECTIVE_DATE_SLACK = timedelta(days=45)


class AcquisitionState(StrEnum):
    SUCCESS = "SUCCESS"
    VALID_EMPTY = "VALID_EMPTY"
    STALE = "STALE"
    FAILED = "FAILED"


class RawAcquisition(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    state: AcquisitionState
    source_url: str
    status_code: int | None = Field(default=None, ge=100, le=599)
    media_type: str | None = None
    content: bytes = b""
    payload: Any = None
    fetched_at: datetime
    error: str | None = None
    retry_count: int = Field(default=0, ge=0)
    endpoint_result: Any = None

    @classmethod
    def success(
        cls,
        *,
        source_url: str,
        status_code: int,
        media_type: str,
        content: bytes,
        payload: Any,
        fetched_at: datetime,
        retry_count: int = 0,
        endpoint_result: Any = None,
    ) -> RawAcquisition:
        return cls(
            state=AcquisitionState.SUCCESS,
            source_url=source_url,
            status_code=status_code,
            media_type=media_type,
            content=content,
            payload=payload,
            fetched_at=fetched_at,
            retry_count=retry_count,
            endpoint_result=endpoint_result,
        )

    @classmethod
    def failed(
        cls,
        *,
        source_url: str,
        error: str,
        retry_count: int = 0,
        status_code: int | None = None,
    ) -> RawAcquisition:
        return cls(
            state=AcquisitionState.FAILED,
            source_url=source_url,
            status_code=status_code,
            fetched_at=datetime.now(UTC),
            error=error,
            retry_count=retry_count,
        )


class ParsedSourcePayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    parser_state: str
    records: tuple[dict[str, Any], ...] = ()
    data_date: date | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    source_row_count: int = Field(default=0, ge=0)
    error: str | None = None


class ParameterContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    trading_date: date
    market_session: str = "OPEN"
    symbols: tuple[str, ...] = ()
    scrip_codes: dict[str, str] = Field(default_factory=dict)
    sector_indices: tuple[str, ...] = ()
    option_expiries: dict[str, str] = Field(default_factory=dict)
    now: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NormalizedSourceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: str
    normalized_source_key: str
    status: ManifestStatus
    parser_state: str
    source_url: str | None = None
    http_status: int | None = None
    media_type: str | None = None
    fetched_at: datetime | None = None
    data_date: date | None = None
    source_row_count: int = Field(default=0, ge=0)
    normalized_row_count: int = Field(default=0, ge=0)
    records: tuple[dict[str, Any], ...] = ()
    payload: dict[str, Any] = Field(default_factory=dict)
    raw_content_hashes: tuple[str, ...] = ()
    normalized_content_hash: str | None = None
    retry_count: int = Field(default=0, ge=0)
    error: str | None = None
    stored_attempt_id: int | None = None


class AcquisitionTransport(Protocol):
    async def fetch_endpoint(
        self, endpoint_key: str, parameters: dict[str, str]
    ) -> RawAcquisition: ...

    async def fetch_resolver(
        self, source_key: str, catalog_url: str, **kwargs: Any
    ) -> RawAcquisition: ...


Normalizer = Callable[
    [MarketDataSourceContract, tuple[RawAcquisition, ...], ParameterContext],
    ParsedSourcePayload,
]


class DefaultMarketDataTransport:
    """Thin adapters over the existing endpoint client and source resolver."""

    def __init__(self) -> None:
        self._client: Any = None

    def _endpoint_client(self) -> Any:
        if self._client is None:
            from .institutional_sources import AsyncEndpointClient

            self._client = AsyncEndpointClient()
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def fetch_endpoint(
        self, endpoint_key: str, parameters: dict[str, str]
    ) -> RawAcquisition:
        from .institutional_sources import FetchState

        result = await self._endpoint_client().fetch(endpoint_key, parameters)
        content = b""
        if result.raw_path:
            path = Path(result.raw_path)
            if path.is_file():
                content = path.read_bytes()
        if not content and result.payload is not None:
            content = json.dumps(
                result.payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        if result.state is FetchState.NO_DATA_NOW:
            state = AcquisitionState.VALID_EMPTY
        elif result.state is FetchState.STALE_FALLBACK:
            state = AcquisitionState.STALE
        elif result.state is FetchState.RAW_ARCHIVED:
            state = AcquisitionState.SUCCESS
        else:
            state = AcquisitionState.FAILED
        return RawAcquisition(
            state=state,
            source_url=result.url,
            status_code=result.status_code,
            media_type=result.media_type,
            content=content,
            payload=result.payload,
            fetched_at=result.fetched_at,
            error=result.reason,
            retry_count=result.attempts,
            endpoint_result=result,
        )

    async def fetch_resolver(
        self, source_key: str, catalog_url: str, **kwargs: Any
    ) -> RawAcquisition:
        from .source_resolver import resolve_and_fetch_source

        resolved = await asyncio.to_thread(
            resolve_and_fetch_source,
            source_key,
            catalog_url,
            today=kwargs.get("trading_date"),
        )
        media_type = resolved.headers.get("content-type", "application/octet-stream")
        payload: Any = None
        if "json" in media_type:
            try:
                payload = json.loads(resolved.content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = None
        state = (
            AcquisitionState.SUCCESS
            if resolved.status_code < 400 and bool(resolved.content)
            else AcquisitionState.FAILED
        )
        return RawAcquisition(
            state=state,
            source_url=resolved.url,
            status_code=resolved.status_code,
            media_type=media_type,
            content=resolved.content,
            payload=payload,
            fetched_at=datetime.now(UTC),
            error=None if state is AcquisitionState.SUCCESS else resolved.resolver_state,
            retry_count=max(0, len(resolved.attempts) - 1),
        )


class DomainCircuitBreaker:
    def __init__(self, *, failure_threshold: int, cooldown_seconds: int) -> None:
        if failure_threshold < 1 or cooldown_seconds < 1:
            raise ValueError("circuit breaker limits must be positive")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def allow(self, domain: str) -> bool:
        opened = self._opened_at.get(domain)
        if opened is None:
            return True
        if time.monotonic() - opened >= self.cooldown_seconds:
            self._opened_at.pop(domain, None)
            self._failures[domain] = 0
            return True
        return False

    def record_success(self, domain: str) -> None:
        self._failures[domain] = 0
        self._opened_at.pop(domain, None)

    def record_failure(self, domain: str) -> None:
        failures = self._failures.get(domain, 0) + 1
        self._failures[domain] = failures
        if failures >= self.failure_threshold:
            self._opened_at[domain] = time.monotonic()


def _decode_data_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _extract_records(payload: Any) -> tuple[dict[str, Any], ...]:
    candidates: list[list[dict[str, Any]]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            rows = [item for item in value if isinstance(item, dict)]
            if rows:
                candidates.append(rows)
            return
        if not isinstance(value, dict):
            return
        for key in (
            "rows",
            "records",
            "recordsSample",
            "events",
            "candidates",
            "data",
        ):
            if key in value:
                visit(value[key])
        if not candidates:
            for nested in value.values():
                if isinstance(nested, (dict, list)):
                    visit(nested)

    visit(payload)
    if not candidates:
        return ()
    return tuple(max(candidates, key=len))


def _endpoint_result(raw: RawAcquisition, endpoint_key: str) -> Any:
    if raw.endpoint_result is not None:
        return raw.endpoint_result
    from .institutional_sources import EndpointFetchResult, FetchState

    state = {
        AcquisitionState.SUCCESS: FetchState.RAW_ARCHIVED,
        AcquisitionState.VALID_EMPTY: FetchState.NO_DATA_NOW,
        AcquisitionState.STALE: FetchState.STALE_FALLBACK,
        AcquisitionState.FAILED: FetchState.BROKEN,
    }[raw.state]
    record_count = len(_extract_records(raw.payload))
    return EndpointFetchResult(
        endpointKey=endpoint_key,
        state=state,
        fetchedAt=raw.fetched_at,
        url=raw.source_url,
        contentHash=hashlib.sha256(raw.content).hexdigest() if raw.content else None,
        mediaType=raw.media_type,
        recordCount=record_count,
        payload=raw.payload,
        canScore=False,
        reason=raw.error,
        statusCode=raw.status_code,
        attempts=raw.retry_count,
    )


def default_normalizer(
    contract: MarketDataSourceContract,
    acquisitions: tuple[RawAcquisition, ...],
    context: ParameterContext,
) -> ParsedSourcePayload:
    adapter_id = contract.parser_or_adapter_id
    if adapter_id.startswith("structured:"):
        from .source_parser import parse_source_content

        parser_key = adapter_id.removeprefix("structured:")

        records: list[dict[str, Any]] = []
        outputs: list[dict[str, Any]] = []
        states: list[str] = []
        data_dates: list[date] = []
        errors: list[str] = []
        source_rows = 0
        for raw in acquisitions:
            if raw.state is AcquisitionState.FAILED:
                states.append("FETCH_FAILED")
                if raw.error:
                    errors.append(raw.error)
                continue
            result = parse_source_content(
                parser_key,
                raw.content,
                url=raw.source_url,
                last_modified=raw.fetched_at.isoformat(),
            )
            states.append(result.parser_state)
            if result.error:
                errors.append(result.error)
            if result.data_date:
                parsed_date = _decode_data_date(result.data_date)
                if parsed_date:
                    data_dates.append(parsed_date)
            output = dict(result.output)
            reported_source_rows = output.get("sourceRowCount")
            if (
                isinstance(reported_source_rows, int)
                and not isinstance(reported_source_rows, bool)
                and reported_source_rows >= 0
            ):
                source_rows += reported_source_rows
            else:
                source_rows += result.record_count
            outputs.append(output)
            records.extend(_extract_records(output))
        usable = [state for state in states if state in {"PARSED_STRUCTURED", "STRUCTURED_OK"}]
        parser_state = (
            "PARSED_STRUCTURED"
            if usable and len(usable) == len(states)
            else "PARTIAL"
            if usable
            else states[-1]
            if states
            else "FETCH_FAILED"
        )
        return ParsedSourcePayload(
            parser_state=parser_state,
            records=tuple(records),
            data_date=max(data_dates) if data_dates else None,
            payload={"outputs": outputs},
            source_row_count=source_rows,
            error="; ".join(errors) or None,
        )

    endpoint_results = [
        _endpoint_result(raw, contract.endpoint_key or contract.source_key)
        for raw in acquisitions
    ]
    if adapter_id == "disclosure_snapshot":
        from .disclosure_intelligence import build_disclosure_snapshot

        normalized: Any = build_disclosure_snapshot(endpoint_results)
    elif adapter_id == "market_activity_snapshot":
        from .market_activity import build_market_activity_snapshot

        normalized = build_market_activity_snapshot(endpoint_results)
    elif adapter_id == "intraday_detail_snapshot":
        from .intraday_stock_details import build_intraday_stock_detail_snapshot

        normalized = build_intraday_stock_detail_snapshot(endpoint_results)
    elif adapter_id == "live_panel_source":
        from .live_panels import normalize_live_result

        if len(endpoint_results) != 1:
            return ParsedSourcePayload(
                parser_state="SCHEMA_MISMATCH",
                error="live_panel_source requires exactly one endpoint result",
            )
        normalized = normalize_live_result(
            endpoint_results[0],
            now=context.now,
            market_trading_date=context.trading_date.isoformat(),
        )
    else:
        return ParsedSourcePayload(
            parser_state="NO_ADAPTER",
            error=f"Unsupported adapter: {adapter_id}",
        )
    payload = (
        normalized.model_dump(mode="json", by_alias=True)
        if isinstance(normalized, BaseModel)
        else dict(normalized)
    )
    records = _extract_records(payload)
    return ParsedSourcePayload(
        parser_state="PARSED_ADAPTER",
        records=records,
        data_date=_decode_data_date(
            payload.get("tradingDate") or payload.get("dataDate")
        ),
        payload=payload,
        source_row_count=sum(result.record_count for result in endpoint_results),
    )


class MarketDataService:
    def __init__(
        self,
        *,
        transport: AcquisitionTransport | None = None,
        normalizer: Normalizer | None = None,
        store: MarketDataStore | None = None,
        global_concurrency: int = 4,
        domain_caps: dict[str, int] | None = None,
        breaker_failure_threshold: int = 3,
        breaker_cooldown_seconds: int = 900,
    ) -> None:
        if global_concurrency < 1:
            raise ValueError("global_concurrency must be positive")
        self.transport = transport or DefaultMarketDataTransport()
        self.normalizer = normalizer or default_normalizer
        self.store = store
        self._global_semaphore = asyncio.Semaphore(global_concurrency)
        configured_caps = domain_caps or {
            "www.nseindia.com": 1,
            "nsearchives.nseindia.com": 1,
            "archives.nseindia.com": 1,
            "api.bseindia.com": 1,
        }
        if any(value < 1 for value in configured_caps.values()):
            raise ValueError("domain caps must be positive")
        self._domain_semaphores = {
            domain.casefold(): asyncio.Semaphore(limit)
            for domain, limit in configured_caps.items()
        }
        self._breaker = DomainCircuitBreaker(
            failure_threshold=breaker_failure_threshold,
            cooldown_seconds=breaker_cooldown_seconds,
        )

    @staticmethod
    def supports_normalizer(contract: MarketDataSourceContract) -> bool:
        return contract.parser_or_adapter_id.startswith("structured:") or (
            contract.parser_or_adapter_id
            in {
                "disclosure_snapshot",
                "market_activity_snapshot",
                "intraday_detail_snapshot",
                "live_panel_source",
            }
        )

    @staticmethod
    def build_parameter_sets(
        contract: MarketDataSourceContract, context: ParameterContext
    ) -> tuple[dict[str, str], ...]:
        provider = contract.parameter_provider
        day = context.trading_date
        formatted = day.strftime("%d/%m/%Y")
        if provider == "none":
            values = ({},)
        elif provider == "calendar_date_window":
            month = day.strftime("%Y-%m")
            values = ({"start": month, "end": month},)
        elif provider == "trading_date_window":
            values = ({"from_date": formatted, "to_date": formatted},)
        elif provider == "inventory_symbol_fanout":
            if not context.symbols:
                raise ValueError(f"{contract.source_key} requires symbols for fan-out")
            values = tuple({"symbol": symbol} for symbol in context.symbols)
        elif provider == "inventory_symbol_date_fanout":
            if not context.symbols:
                raise ValueError(f"{contract.source_key} requires symbols for fan-out")
            values = tuple(
                {"symbol": symbol, "from_date": formatted, "to_date": formatted}
                for symbol in context.symbols
            )
        elif provider == "bse_scrip_date_fanout":
            if not context.scrip_codes:
                raise ValueError(f"{contract.source_key} requires scrip codes for fan-out")
            values = tuple(
                {
                    "scripcode": code,
                    "from_date": formatted,
                    "to_date": formatted,
                }
                for _, code in sorted(context.scrip_codes.items())
            )
        elif provider == "sector_index_fanout":
            if not context.sector_indices:
                raise ValueError(f"{contract.source_key} requires sector indices for fan-out")
            values = tuple(
                {"sector_index": sector} for sector in context.sector_indices
            )
        elif provider == "option_symbol_expiry_fanout":
            if not context.option_expiries:
                raise ValueError(
                    f"{contract.source_key} requires bounded option symbols and expiries"
                )
            values = tuple(
                {"symbol": symbol, "expiry": expiry}
                for symbol, expiry in sorted(context.option_expiries.items())
            )
        else:
            raise ValueError(f"Unsupported parameter provider: {provider}")
        for parameters in values:
            missing = [key for key in contract.required_parameters if key not in parameters]
            if missing:
                raise ValueError(
                    f"{contract.source_key} parameter provider missed: {', '.join(missing)}"
                )
        return values

    @staticmethod
    def _domain(contract: MarketDataSourceContract) -> str:
        first_url = contract.canonical_url.split(" | ", 1)[0]
        return (urlparse(first_url).hostname or "unknown").casefold()

    async def _fetch_limited(
        self,
        contract: MarketDataSourceContract,
        operation: Callable[[], Awaitable[RawAcquisition]],
    ) -> RawAcquisition:
        domain = self._domain(contract)
        domain_semaphore = self._domain_semaphores.get(domain)

        async def execute_checked() -> RawAcquisition:
            # Re-check only after this request reaches the front of its domain
            # queue; earlier failures may have opened the circuit meanwhile.
            if not self._breaker.allow(domain):
                return RawAcquisition.failed(
                    source_url=contract.canonical_url,
                    error=f"Domain circuit breaker is open for {domain}",
                )
            result = await operation()
            if result.state is AcquisitionState.FAILED:
                self._breaker.record_failure(domain)
            else:
                self._breaker.record_success(domain)
            return result

        async with self._global_semaphore:
            if domain_semaphore is None:
                return await execute_checked()
            else:
                async with domain_semaphore:
                    return await execute_checked()

    async def _acquire(
        self,
        contract: MarketDataSourceContract,
        context: ParameterContext,
    ) -> tuple[RawAcquisition, ...]:
        if contract.acquisition_owner is AcquisitionOwner.RESOLVER_MONITOR:
            result = await self._fetch_limited(
                contract,
                lambda: self.transport.fetch_resolver(
                    contract.source_key,
                    contract.canonical_url,
                    trading_date=context.trading_date,
                ),
            )
            return (result,)
        parameter_sets = self.build_parameter_sets(contract, context)
        endpoint_keys = contract.fanout_endpoint_keys or (
            (contract.endpoint_key,) if contract.endpoint_key else ()
        )
        if not endpoint_keys:
            return (
                RawAcquisition.failed(
                    source_url=contract.canonical_url,
                    error="No endpoint key is configured",
                ),
            )
        tasks = [
            self._fetch_limited(
                contract,
                lambda endpoint_key=endpoint_key, parameters=parameters: (
                    self.transport.fetch_endpoint(endpoint_key, parameters)
                ),
            )
            for endpoint_key in endpoint_keys
            for parameters in parameter_sets
        ]
        return tuple(await asyncio.gather(*tasks))

    @staticmethod
    def _empty_status(
        contract: MarketDataSourceContract,
        context: ParameterContext,
        parser_state: str,
    ) -> ManifestStatus:
        parser_ok = parser_state in {
            "PARSED_STRUCTURED",
            "STRUCTURED_OK",
            "PARSED_ADAPTER",
            "VALID_EMPTY_TRANSPORT",
        }
        validator = contract.validator_id
        if not parser_ok:
            return ManifestStatus.FAILED
        if validator == "schema_date_valid_empty":
            return ManifestStatus.VALID_EMPTY
        if validator == "publication_window_non_empty":
            return ManifestStatus.WAITING_FOR_PUBLICATION
        if validator == "previous_period_retention":
            return ManifestStatus.STALE_LAST_GOOD
        if validator == "market_open_non_empty":
            return (
                ManifestStatus.FAILED
                if context.market_session == "OPEN"
                else ManifestStatus.VALID_EMPTY
            )
        if validator == "session_window_valid_empty":
            return (
                ManifestStatus.FAILED
                if context.market_session == "OPEN"
                else ManifestStatus.VALID_EMPTY
            )
        return ManifestStatus.FAILED

    def _normalize(
        self,
        contract: MarketDataSourceContract,
        acquisitions: tuple[RawAcquisition, ...],
        context: ParameterContext,
    ) -> NormalizedSourceResult:
        try:
            parsed = self.normalizer(contract, acquisitions, context)
        except Exception as exc:
            parsed = ParsedSourcePayload(
                parser_state="WAIT_PARSE_ERROR",
                error=f"{type(exc).__name__}: {exc}",
            )
        failures = [item for item in acquisitions if item.state is AcquisitionState.FAILED]
        stale = [item for item in acquisitions if item.state is AcquisitionState.STALE]
        transport_valid_empty = bool(acquisitions) and all(
            item.state is AcquisitionState.VALID_EMPTY for item in acquisitions
        )
        usable_parser = parsed.parser_state in {
            "PARSED_STRUCTURED",
            "STRUCTURED_OK",
            "PARSED_ADAPTER",
        }
        validation_error: str | None = None
        if parsed.records:
            if parsed.data_date and parsed.data_date > context.trading_date:
                allow_effective = (
                    contract.source_key in _FUTURE_EFFECTIVE_DATE_KEYS
                    and parsed.data_date
                    <= context.trading_date + _FUTURE_EFFECTIVE_DATE_SLACK
                )
                if allow_effective:
                    # Keep rows; stamp store dataDate as trading day (not expiry/ban-for).
                    parsed = parsed.model_copy(update={"data_date": context.trading_date})
                else:
                    status = ManifestStatus.FAILED
                    validation_error = "normalized data date is in the future"
            if validation_error is None:
                if parsed.parser_state == "PARTIAL" or failures:
                    status = ManifestStatus.PARTIAL
                elif not usable_parser:
                    status = ManifestStatus.FAILED
                    validation_error = (
                        f"parser state {parsed.parser_state} cannot publish records"
                    )
                elif stale:
                    status = ManifestStatus.STALE_LAST_GOOD
                else:
                    status = ManifestStatus.SUCCESS_NEW
        else:
            status = self._empty_status(
                contract,
                context,
                "VALID_EMPTY_TRANSPORT" if transport_valid_empty else parsed.parser_state,
            )
        first = acquisitions[0] if acquisitions else None
        raw_hashes = tuple(
            hashlib.sha256(item.content).hexdigest()
            for item in acquisitions
            if item.content
        )
        normalized_payload = {
            "sourceKey": contract.source_key,
            "normalizedSourceKey": contract.normalized_source_key,
            "parserState": parsed.parser_state,
            "dataDate": parsed.data_date.isoformat() if parsed.data_date else None,
            "records": list(parsed.records),
            "payload": parsed.payload,
            "rawContentHashes": list(raw_hashes),
        }
        normalized_bytes = json.dumps(
            normalized_payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        errors = [
            item.error
            for item in acquisitions
            if item.error
            and item.state in {AcquisitionState.FAILED, AcquisitionState.STALE}
        ]
        if parsed.error:
            errors.append(parsed.error)
        if validation_error:
            errors.append(validation_error)
        return NormalizedSourceResult(
            source_key=contract.source_key,
            normalized_source_key=contract.normalized_source_key,
            status=status,
            parser_state=parsed.parser_state,
            source_url=first.source_url if first else contract.canonical_url,
            http_status=first.status_code if first else None,
            media_type=first.media_type if first else None,
            fetched_at=max(
                (item.fetched_at for item in acquisitions),
                default=context.now,
            ),
            data_date=parsed.data_date,
            source_row_count=parsed.source_row_count,
            normalized_row_count=len(parsed.records),
            records=parsed.records,
            payload=normalized_payload,
            raw_content_hashes=raw_hashes,
            normalized_content_hash=hashlib.sha256(normalized_bytes).hexdigest(),
            retry_count=sum(item.retry_count for item in acquisitions),
            error="; ".join(errors) or None,
        )

    def _persist(
        self,
        result: NormalizedSourceResult,
        *,
        context: ParameterContext,
        run_id: str,
        slot: str,
    ) -> NormalizedSourceResult:
        if self.store is None:
            return result
        if result.status is ManifestStatus.SUCCESS_NEW:
            payload = json.dumps(
                result.payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            stored = self.store.commit_success(
                run_id=run_id,
                source_key=result.source_key,
                trading_date=context.trading_date,
                slot=slot,
                attempted_at=context.now,
                fetched_at=result.fetched_at or context.now,
                data_date=result.data_date,
                source_url=result.source_url or "",
                http_status=result.http_status or 200,
                media_type="application/vnd.trendforge.normalized+json",
                content=payload,
                extension="json",
                normalized_row_count=result.normalized_row_count,
                retry_count=result.retry_count,
            )
        else:
            stored = self.store.record_attempt(
                run_id=run_id,
                source_key=result.source_key,
                trading_date=context.trading_date,
                slot=slot,
                attempted_at=context.now,
                status=result.status,
                source_url=result.source_url,
                http_status=result.http_status,
                error=result.error,
                retry_count=result.retry_count,
            )
        return result.model_copy(
            update={
                "status": stored.status,
                "stored_attempt_id": stored.attempt_id,
            }
        )

    async def run_source(
        self,
        contract: MarketDataSourceContract,
        *,
        context: ParameterContext,
        run_id: str | None = None,
        slot: str = "manual",
    ) -> NormalizedSourceResult:
        try:
            acquisitions = await self._acquire(contract, context)
            result = self._normalize(contract, acquisitions, context)
        except Exception as exc:
            result = NormalizedSourceResult(
                source_key=contract.source_key,
                normalized_source_key=contract.normalized_source_key,
                status=ManifestStatus.FAILED,
                parser_state="ACQUISITION_FAILED",
                error=f"{type(exc).__name__}: {exc}",
            )
        return (
            self._persist(result, context=context, run_id=run_id, slot=slot)
            if self.store is not None and run_id is not None
            else result
        )

    async def run_sources(
        self,
        contracts: tuple[MarketDataSourceContract, ...],
        *,
        context: ParameterContext,
        run_id: str | None = None,
        slot: str = "manual",
    ) -> dict[str, NormalizedSourceResult]:
        groups: list[tuple[MarketDataSourceContract, ...]] = []
        reuse: dict[str, list[MarketDataSourceContract]] = {}
        for contract in contracts:
            if contract.fetch_group_mode is FetchGroupMode.RESPONSE_REUSE:
                reuse.setdefault(contract.fetch_group, []).append(contract)
            else:
                groups.append((contract,))
        groups.extend(tuple(items) for items in reuse.values())

        async def process_group(
            group: tuple[MarketDataSourceContract, ...]
        ) -> dict[str, NormalizedSourceResult]:
            if len(group) == 1 or group[0].fetch_group_mode is not FetchGroupMode.RESPONSE_REUSE:
                contract = group[0]
                return {
                    contract.source_key: await self.run_source(
                        contract,
                        context=context,
                        run_id=run_id,
                        slot=slot,
                    )
                }
            try:
                acquisitions = await self._acquire(group[0], context)
            except Exception as exc:
                acquisitions = (
                    RawAcquisition.failed(
                        source_url=group[0].canonical_url,
                        error=f"{type(exc).__name__}: {exc}",
                    ),
                )
            output: dict[str, NormalizedSourceResult] = {}
            for contract in group:
                result = self._normalize(contract, acquisitions, context)
                if self.store is not None and run_id is not None:
                    result = self._persist(
                        result, context=context, run_id=run_id, slot=slot
                    )
                output[contract.source_key] = result
            return output

        completed = await asyncio.gather(*(process_group(group) for group in groups))
        return {
            source_key: result
            for group_result in completed
            for source_key, result in group_result.items()
        }
