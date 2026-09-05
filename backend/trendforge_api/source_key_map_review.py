"""CROSS-002 living source-key map and fail-closed review baseline.

Hash-generated ``source:<digest>`` values preserve endpoint lineage only. They
are deliberately excluded from the named source-key map and can never gain
gate or execution authority through this module.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field


REVIEW_VERSION = "CROSS-002-2026-09-03-v3"
REVIEWED_NAMED_INVENTORY_COUNT = 157
REVIEWED_RUNTIME_CATALOG_COUNT = 135
REVIEWED_LIVING_MAP_COUNT = 179
REVIEWED_NAMED_INVENTORY_SHA256 = (
    "e746a54522d60fb1634c03187139ea1e709143aeb9403527cb6c94e6b5018a10"
)
REVIEWED_RUNTIME_CATALOG_SHA256 = (
    "db3fc74dd1ab16ae25311f2d4d07a97687bbe588d0cc4608c4ee92f3d5805acd"
)
REVIEWED_LIVING_MAP_SHA256 = (
    "d24a2ddd9370080f93c5709c892152fd8522f24731a3a5949012a514ae5593f6"
)


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


def _key_digest(values: set[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


class SourceKeyOrigin(StrEnum):
    INVENTORY_AND_RUNTIME = "INVENTORY_AND_RUNTIME"
    INVENTORY_ONLY = "INVENTORY_ONLY"
    RUNTIME_ONLY = "RUNTIME_ONLY"


class SourceKeyMapDisposition(StrEnum):
    MAPPED_QUARANTINED_INCOMPLETE = "MAPPED_QUARANTINED_INCOMPLETE"
    INVENTORY_ONLY_RUNTIME_UNWIRED = "INVENTORY_ONLY_RUNTIME_UNWIRED"
    RUNTIME_ONLY_INVENTORY_UNREGISTERED = "RUNTIME_ONLY_INVENTORY_UNREGISTERED"


class EndpointMapDisposition(StrEnum):
    NAMED_SOURCE_MAPPED = "NAMED_SOURCE_MAPPED"
    UNASSIGNED_ENDPOINT_LINEAGE = "UNASSIGNED_ENDPOINT_LINEAGE"


class SourceKeyMapRecord(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel, populate_by_name=True, frozen=True
    )

    source_key: str = Field(alias="sourceKey")
    origin: SourceKeyOrigin
    disposition: SourceKeyMapDisposition
    inventory_contract_id: str | None = Field(default=None, alias="inventoryContractId")
    runtime_catalog_key: str | None = Field(default=None, alias="runtimeCatalogKey")
    inventory_ids: list[str] = Field(default_factory=list, alias="inventoryIds")
    endpoint_ids: list[str] = Field(default_factory=list, alias="endpointIds")
    decision_jobs: list[str] = Field(default_factory=list, alias="decisionJobs")
    runtime_category: str | None = Field(default=None, alias="runtimeCategory")
    runtime_parser_status: str | None = Field(default=None, alias="runtimeParserStatus")
    contract_status: str = Field(alias="contractStatus")
    maturity_state: str = Field(alias="maturityState")
    review_state: str = Field(alias="reviewState")
    safe_use: str = Field(alias="safeUse")
    blocked_use: str = Field(alias="blockedUse")
    next_action: str = Field(alias="nextAction")
    maturity_reviewed: bool = Field(alias="maturityReviewed")
    activation_reviewed: bool = Field(alias="activationReviewed")
    activation_blockers: list[str] = Field(
        default_factory=list, alias="activationBlockers"
    )
    can_confirm: bool = Field(default=False, alias="canConfirm")
    gate_permission: bool = Field(default=False, alias="gatePermission")
    execution_authorized: bool = Field(default=False, alias="executionAuthorized")


class EndpointSourceMapRecord(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel, populate_by_name=True, frozen=True
    )

    endpoint_id: str = Field(alias="endpointId")
    canonical_url: str = Field(alias="canonicalUrl")
    source_keys: list[str] = Field(default_factory=list, alias="sourceKeys")
    generated_lineage_ids: list[str] = Field(
        default_factory=list, alias="generatedLineageIds"
    )
    inventory_ids: list[str] = Field(default_factory=list, alias="inventoryIds")
    disposition: EndpointMapDisposition
    review_state: str = Field(alias="reviewState")
    quarantined: bool
    gate_eligible: bool = Field(default=False, alias="gateEligible")


@dataclass(frozen=True)
class SourceKeyMapBuild:
    records: list[SourceKeyMapRecord]
    endpoint_records: list[EndpointSourceMapRecord]
    review_valid: bool
    review_errors: list[str]
    named_inventory_count: int
    generated_lineage_count: int
    runtime_catalog_count: int
    shared_count: int
    inventory_only_count: int
    runtime_only_count: int
    living_map_count: int
    unassigned_endpoint_count: int
    named_inventory_sha256: str
    runtime_catalog_sha256: str
    living_map_sha256: str
    governance_ready: bool
    reviewed_source_count: int
    unreviewed_source_count: int
    activation_reviewed_count: int
    gate_authorized_count: int


def _review_errors(named: set[str], catalog: set[str]) -> list[str]:
    living = named | catalog
    checks = (
        (
            "named_inventory_count",
            len(named),
            REVIEWED_NAMED_INVENTORY_COUNT,
        ),
        (
            "runtime_catalog_count",
            len(catalog),
            REVIEWED_RUNTIME_CATALOG_COUNT,
        ),
        ("living_map_count", len(living), REVIEWED_LIVING_MAP_COUNT),
        (
            "named_inventory_sha256",
            _key_digest(named),
            REVIEWED_NAMED_INVENTORY_SHA256,
        ),
        (
            "runtime_catalog_sha256",
            _key_digest(catalog),
            REVIEWED_RUNTIME_CATALOG_SHA256,
        ),
        (
            "living_map_sha256",
            _key_digest(living),
            REVIEWED_LIVING_MAP_SHA256,
        ),
    )
    return [
        f"{name}:actual={actual};expected={expected}"
        for name, actual, expected in checks
        if actual != expected
    ]


def build_source_key_map(
    source_contracts: Sequence[Any],
    normalized_endpoints: Sequence[Any],
    runtime_catalog: Sequence[Any],
) -> SourceKeyMapBuild:
    """Build an exact union map without converting endpoint hashes into sources."""

    contracts = {item.source_contract_id: item for item in source_contracts}
    named = {key for key in contracts if not key.startswith("source:")}
    generated = set(contracts) - named
    catalog_by_key = {item.key: item for item in runtime_catalog}
    catalog = set(catalog_by_key)
    living = named | catalog
    errors = _review_errors(named, catalog)
    review_state = "REVIEWED_BASELINE" if not errors else "BASELINE_DRIFT"

    records: list[SourceKeyMapRecord] = []
    for key in sorted(living):
        contract = contracts.get(key)
        descriptor = catalog_by_key.get(key)
        if contract is not None and descriptor is not None:
            origin = SourceKeyOrigin.INVENTORY_AND_RUNTIME
            disposition = SourceKeyMapDisposition.MAPPED_QUARANTINED_INCOMPLETE
            next_action = contract.next_action
        elif contract is not None:
            origin = SourceKeyOrigin.INVENTORY_ONLY
            disposition = SourceKeyMapDisposition.INVENTORY_ONLY_RUNTIME_UNWIRED
            next_action = "Review runtime adapter ownership before activation"
        else:
            origin = SourceKeyOrigin.RUNTIME_ONLY
            disposition = SourceKeyMapDisposition.RUNTIME_ONLY_INVENTORY_UNREGISTERED
            next_action = "Register exact inventory lineage before activation"

        blockers: list[str] = []
        if errors:
            blockers.append("SOURCE_MAP_BASELINE_DRIFT")
        if contract is None:
            blockers.append("MISSING_INVENTORY_LINEAGE")
        else:
            if contract.contract_status != "COMPLETE":
                blockers.append("INCOMPLETE_SOURCE_CONTRACT")
            blockers.extend(
                f"MISSING_CONTRACT_FIELD:{field}"
                for field in contract.missing_extended_fields
            )
            if not contract.gate_permission:
                blockers.append("GATE_PERMISSION_NOT_GRANTED")
        if descriptor is None:
            blockers.append("MISSING_RUNTIME_CATALOG_CONTRACT")
        else:
            blockers.append("RUNTIME_PROOF_NOT_COMPILER_AUTHORIZED")

        records.append(
            SourceKeyMapRecord(
                sourceKey=key,
                origin=origin,
                disposition=disposition,
                inventoryContractId=key if contract is not None else None,
                runtimeCatalogKey=key if descriptor is not None else None,
                inventoryIds=list(contract.inventory_ids) if contract else [],
                endpointIds=list(contract.endpoint_ids) if contract else [],
                decisionJobs=list(contract.decision_jobs) if contract else [],
                runtimeCategory=descriptor.category if descriptor else None,
                runtimeParserStatus=descriptor.parser_status if descriptor else None,
                contractStatus=(
                    contract.contract_status
                    if contract is not None
                    else "QUARANTINED_INCOMPLETE"
                ),
                maturityState=(
                    contract.maturity_state.value
                    if contract is not None
                    else "REGISTERED"
                ),
                reviewState=review_state,
                safeUse=(
                    contract.safe_use
                    if contract is not None
                    else "Runtime catalog visibility and research inspection only"
                ),
                blockedUse=(
                    contract.blocked_use
                    if contract is not None
                    else (
                        "No CONFIRMED, gate, quantity, execution or live-trade "
                        "authority without inventory lineage"
                    )
                ),
                nextAction=next_action,
                maturityReviewed=not errors,
                activationReviewed=not errors,
                activationBlockers=sorted(set(blockers)),
                canConfirm=False,
                gatePermission=False,
                executionAuthorized=False,
            )
        )

    endpoint_records: list[EndpointSourceMapRecord] = []
    for endpoint in sorted(normalized_endpoints, key=lambda item: item.canonical_url):
        named_ids = sorted(
            key for key in endpoint.source_contract_ids if not key.startswith("source:")
        )
        generated_ids = sorted(
            key for key in endpoint.source_contract_ids if key.startswith("source:")
        )
        endpoint_records.append(
            EndpointSourceMapRecord(
                endpointId=endpoint.endpoint_id,
                canonicalUrl=endpoint.canonical_url,
                sourceKeys=named_ids,
                generatedLineageIds=generated_ids,
                inventoryIds=list(endpoint.inventory_ids),
                disposition=(
                    EndpointMapDisposition.NAMED_SOURCE_MAPPED
                    if named_ids
                    else EndpointMapDisposition.UNASSIGNED_ENDPOINT_LINEAGE
                ),
                reviewState=review_state,
                quarantined=bool(endpoint.quarantined or not named_ids),
                gateEligible=False,
            )
        )

    governance_ready = bool(
        not errors
        and len(records) == len(living)
        and len({item.source_key for item in records}) == len(living)
        and len(endpoint_records) == len(normalized_endpoints)
        and all(item.activation_blockers for item in records)
        and all(not item.gate_permission for item in records)
    )
    return SourceKeyMapBuild(
        records=records,
        endpoint_records=endpoint_records,
        review_valid=not errors,
        review_errors=errors,
        named_inventory_count=len(named),
        generated_lineage_count=len(generated),
        runtime_catalog_count=len(catalog),
        shared_count=len(named & catalog),
        inventory_only_count=len(named - catalog),
        runtime_only_count=len(catalog - named),
        living_map_count=len(living),
        unassigned_endpoint_count=sum(
            item.disposition is EndpointMapDisposition.UNASSIGNED_ENDPOINT_LINEAGE
            for item in endpoint_records
        ),
        named_inventory_sha256=_key_digest(named),
        runtime_catalog_sha256=_key_digest(catalog),
        living_map_sha256=_key_digest(living),
        governance_ready=governance_ready,
        reviewed_source_count=len(records) if not errors else 0,
        unreviewed_source_count=0 if not errors else len(records),
        activation_reviewed_count=len(records) if not errors else 0,
        gate_authorized_count=0,
    )
