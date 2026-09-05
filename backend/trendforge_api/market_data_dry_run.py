from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .market_data_registry import load_market_data_registry
from .market_data_scheduler import IST, MarketDataScheduler
from .market_data_service import (
    MarketDataService,
    ParameterContext,
    ParsedSourcePayload,
    RawAcquisition,
)
from .market_data_store import MarketDataStore


FIXTURE_TRADING_DATE = date(2026, 8, 5)
FIXTURE_SLOT = "0917"


class NoNetworkFixtureTransport:
    """Deterministic transport used only by the explicit MD69 dry-run command."""

    def __init__(self, *, fetched_at: datetime) -> None:
        self.fetched_at = fetched_at
        self.endpoint_calls: list[tuple[str, dict[str, str]]] = []
        self.resolver_calls: list[tuple[str, str]] = []

    @staticmethod
    def _content(kind: str, key: str, parameters: dict[str, str]) -> bytes:
        return json.dumps(
            {"fixture": True, "kind": kind, "key": key, "parameters": parameters},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    async def fetch_endpoint(
        self, endpoint_key: str, parameters: dict[str, str]
    ) -> RawAcquisition:
        copied = dict(parameters)
        self.endpoint_calls.append((endpoint_key, copied))
        content = self._content("endpoint", endpoint_key, copied)
        return RawAcquisition.success(
            source_url=f"fixture://endpoint/{endpoint_key}",
            status_code=200,
            media_type="application/json",
            content=content,
            payload=json.loads(content),
            fetched_at=self.fetched_at,
        )

    async def fetch_resolver(
        self, source_key: str, catalog_url: str, **kwargs
    ) -> RawAcquisition:
        self.resolver_calls.append((source_key, catalog_url))
        content = self._content("resolver", source_key, {})
        return RawAcquisition.success(
            source_url=f"fixture://resolver/{source_key}",
            status_code=200,
            media_type="application/json",
            content=content,
            payload=json.loads(content),
            fetched_at=self.fetched_at,
        )


def _fixture_normalizer(contract, acquisitions, context) -> ParsedSourcePayload:
    return ParsedSourcePayload(
        parser_state="PARSED_ADAPTER",
        records=(
            {
                "symbol": contract.source_key.upper(),
                "fixture": True,
                "acquisitionCount": len(acquisitions),
            },
        ),
        data_date=context.trading_date,
        payload={"fixture": True, "sourceKey": contract.source_key},
        source_row_count=len(acquisitions),
    )


def _fixture_calendar(trading_date: date):
    def evaluate(_at: datetime) -> dict[str, Any]:
        return {
            "state": "OPEN_NORMAL",
            "isTradingDay": True,
            "canRunScheduledScan": True,
            "tradingDate": trading_date.isoformat(),
            "reason": "MD69 deterministic no-network fixture",
        }

    return evaluate


def _fixture_context(
    trading_date: date, session: str, at: datetime
) -> ParameterContext:
    return ParameterContext(
        trading_date=trading_date,
        market_session=session,
        symbols=("RELIANCE",),
        scrip_codes={"RELIANCE": "500325"},
        sector_indices=("NIFTY 50",),
        now=at,
    )


async def run_no_network_dry_run(
    output_root: Path,
    *,
    trading_date: date = FIXTURE_TRADING_DATE,
    slot: str = FIXTURE_SLOT,
) -> dict[str, Any]:
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    at = datetime(
        trading_date.year,
        trading_date.month,
        trading_date.day,
        int(slot[:2]),
        int(slot[2:]),
        tzinfo=IST,
    ).astimezone(UTC)
    registry = load_market_data_registry()
    store = MarketDataStore(root=root / "market_data", db_path=root / "fixture.db")
    transport = NoNetworkFixtureTransport(fetched_at=at)
    service = MarketDataService(
        transport=transport,
        normalizer=_fixture_normalizer,
        store=store,
        global_concurrency=4,
    )
    scheduler = MarketDataScheduler(
        registry=registry,
        store=store,
        service=service,
        enabled=True,
        allow_provisional_for_testing=True,
        calendar_evaluator=_fixture_calendar(trading_date),
        context_provider=_fixture_context,
    )
    result = await scheduler.run_snapshot(slot=slot, at=at)
    status = scheduler.status()
    report = {
        "schemaVersion": "trendforge.md69.no-network-dry-run.v1",
        "networkMode": "FIXTURE_ONLY_NO_NETWORK",
        "productionActivation": False,
        "registrySha256": registry.registry_sha256,
        "registrySourceCount": len(registry.contracts),
        "scheduleAuthority": registry.schedule_authority.value,
        "activationReady": registry.activation_ready,
        "run": result.model_dump(mode="json"),
        "transport": {
            "endpointCalls": len(transport.endpoint_calls),
            "resolverCalls": len(transport.resolver_calls),
            "totalCalls": len(transport.endpoint_calls) + len(transport.resolver_calls),
        },
        "status": status,
    }
    report_path = root / "dry_run_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {**report, "reportPath": str(report_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MD69 with offline fixtures only")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--trading-date", type=date.fromisoformat, default=FIXTURE_TRADING_DATE)
    parser.add_argument("--slot", choices=("0900", "0917", "1030", "1230", "1330", "1500"), default=FIXTURE_SLOT)
    args = parser.parse_args()
    report = asyncio.run(
        run_no_network_dry_run(
            args.output_root,
            trading_date=args.trading_date,
            slot=args.slot,
        )
    )
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
