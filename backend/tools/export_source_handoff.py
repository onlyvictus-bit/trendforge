from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from trendforge_api.source_monitor import SOURCE_CATALOG
from trendforge_api.source_registry_contracts import (
    classify_registry_urls,
    load_saved_link_inventory,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = PROJECT_ROOT / "docs" / "ALL_211_SOURCE_HANDOFF.csv"


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    )
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            query,
            "",
        )
    )


def disposition(role: str) -> tuple[str, str]:
    if role == "OFFICIAL_OR_PRIMARY":
        return (
            "OFFICIAL_CONTRACT_CANDIDATE",
            "Verify direct artifact/API, archive raw bytes, parse rows, date and test before gate use.",
        )
    if role == "LICENSED_CANDIDATE":
        return (
            "LICENSE_AND_ADAPTER_REQUIRED",
            "Confirm entitlement and API contract; implement only behind the licensed-feed adapter.",
        )
    if role == "SECONDARY_DISCOVERY":
        return (
            "DISCOVERY_ONLY",
            "Use only to find a lead; reconcile every claim to an official source and never count twice.",
        )
    if role == "OPEN_SOURCE_REFERENCE":
        return (
            "IMPLEMENTATION_REFERENCE_ONLY",
            "Audit license, maintenance and algorithm; do not use its website output as market proof.",
        )
    if role == "REFERENCE_ONLY":
        return (
            "DESIGN_REFERENCE_ONLY",
            "Use for UI, workflow or ratio comparison only; never fetch it as scanner authority.",
        )
    if role == "LOCAL_APPLICATION":
        return (
            "LOCAL_OPERATIONS_ONLY",
            "Use for local health or integration testing, not market evidence.",
        )
    return (
        "QUARANTINE",
        "Do not use until domain authority and legal role are reviewed.",
    )


def main() -> None:
    urls = load_saved_link_inventory()
    contracts = classify_registry_urls(urls)
    active_by_url = {
        canonical_url(item.url): item
        for item in SOURCE_CATALOG
        if item.url.startswith(("http://", "https://"))
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "hostname",
                "url",
                "source_role",
                "allowed_jobs",
                "url_can_unlock_ready",
                "authority_reason",
                "active_source_key",
                "active_parser_status",
                "integration_disposition",
                "other_ai_task",
            ],
        )
        writer.writeheader()
        for index, contract in enumerate(contracts, start=1):
            active = active_by_url.get(canonical_url(contract.url))
            action, task = disposition(contract.source_role)
            writer.writerow(
                {
                    "id": index,
                    "hostname": contract.hostname,
                    "url": contract.url,
                    "source_role": contract.source_role,
                    "allowed_jobs": "|".join(contract.allowed_jobs),
                    "url_can_unlock_ready": str(contract.can_unlock_ready).lower(),
                    "authority_reason": contract.authority_reason,
                    "active_source_key": active.key if active else "",
                    "active_parser_status": active.parser_status if active else "",
                    "integration_disposition": action,
                    "other_ai_task": task,
                }
            )
    print(f"wrote {len(contracts)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
