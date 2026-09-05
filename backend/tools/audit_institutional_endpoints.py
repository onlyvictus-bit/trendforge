from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from trendforge_api.institutional_sources import ENDPOINTS, AsyncEndpointClient
from trendforge_api.observability import configure_logging


DEFAULT_PARAMETERS = {
    "symbol": "RELIANCE",
    "scripcode": "500325",
    "scheme_code": "118989",
}
LOGGER = configure_logging()


async def audit(output: Path, concurrency: int) -> dict:
    requests = [
        (
            spec.key,
            {
                parameter: DEFAULT_PARAMETERS[parameter]
                for parameter in spec.required_parameters
            },
        )
        for spec in ENDPOINTS.values()
    ]
    client = AsyncEndpointClient()
    try:
        results = await client.fetch_many(requests, concurrency=concurrency)
    finally:
        await client.aclose()
    payload = {
        "createdAt": datetime.now(UTC).isoformat(),
        "contractCount": len(ENDPOINTS),
        "states": dict(Counter(result.state.value for result in results)),
        "scoreableCount": sum(result.can_score for result in results),
        "results": [
            result.model_dump(mode="json", by_alias=True) for result in results
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Archive and classify every configured institutional endpoint."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../docs/INSTITUTIONAL_ENDPOINT_AUDIT_CURRENT.json"),
    )
    parser.add_argument("--concurrency", type=int, default=4)
    arguments = parser.parse_args()
    result = asyncio.run(audit(arguments.output.resolve(), arguments.concurrency))
    summary = {
        key: result[key] for key in ("contractCount", "states", "scoreableCount")
    }
    LOGGER.info(
        "institutional_endpoint_audit_complete %s", json.dumps(summary, sort_keys=True)
    )


if __name__ == "__main__":
    main()
