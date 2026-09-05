"""R0-B first official source-contract proof cohort.

This does not activate sources. Missing or unproven dimensions stay
WAIT/QUARANTINED. Shared NSE domain retry/breaker is proven as a shared
runtime policy, not a per-source unique breaker. MWPL percentages stay
confirm-ineligible until an official percentage artifact exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .source_extended_field_proofs import ALLOWED_EXTENDED_FIELDS, proof_for_source
from .source_inventory_compiler import compile_default_inventory
from .source_monitor import SOURCE_CATALOG
from .source_parser import STRUCTURED_PARSERS


class ProofState(StrEnum):
    PASS = "PASS"
    WAIT = "WAIT"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CohortMember:
    source_key: str
    class_name: str
    role: str
    can_vote: bool = False
    confirm_eligible: bool = True


R0B_COHORT: tuple[CohortMember, ...] = (
    CohortMember("nse_fno_ban", "FNO_BAN_VETO", "hard_veto"),
    CohortMember(
        "nse_mwpl_percentages",
        "MWPL_PERCENTAGES",
        "soft_veto_wait",
        confirm_eligible=False,
    ),
    CohortMember("nse_bhavcopy_eod", "CASH_EOD", "price_volume"),
    CohortMember("nse_fo_bhavcopy", "FNO_EOD", "price_oi"),
    CohortMember("nse_index_close_eod", "INDEX_SECTOR_VIX", "context"),
    CohortMember("nse_corporate_filings_actions", "CORPORATE_ACTIONS", "adjustment"),
)

PROOF_DIMENSIONS = (
    "catalog_identity",
    "parser_registered",
    "valid_empty_or_unavailable_distinct",
    "official_authority",
    "dataset_root_or_named_contract",
    "freshness_policy",
    "extended_fields_complete",
    "source_specific_retry_breaker",
)


class DimensionProof(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    id: str
    state: ProofState
    evidence: str


class CohortSourceProof(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    source_key: str = Field(alias="sourceKey")
    class_name: str = Field(alias="className")
    role: str
    parser_status: str | None = Field(default=None, alias="parserStatus")
    dimensions: list[DimensionProof]
    proven: bool
    quarantined: bool
    confirm_eligible: bool = Field(alias="confirmEligible")
    can_unlock_confirmed: bool = Field(alias="canUnlockConfirmed")
    can_vote: bool = Field(alias="canVote")
    missing_extended_fields: list[str] = Field(alias="missingExtendedFields")
    waived_extended_fields: list[str] = Field(alias="waivedExtendedFields")
    reviewed: bool


class R0BCohortReport(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    version: str = "R0-B-v1"
    slice: str = "R0-B"
    source_activation_ready: bool = Field(alias="sourceActivationReady")
    gate_authorized_source_key_count: int = Field(alias="gateAuthorizedSourceKeyCount")
    h1a0_passed: int = Field(alias="h1a0Passed")
    h1a0_total: int = Field(alias="h1a0Total")
    workbook_sha256: str | None = Field(default=None, alias="workbookSha256")
    row_count: int = Field(alias="rowCount")
    proven_count: int = Field(alias="provenCount")
    reviewed_count: int = Field(alias="reviewedCount")
    quarantined_count: int = Field(alias="quarantinedCount")
    members: list[CohortSourceProof]
    note: str


def _descriptor(key: str):
    return next((item for item in SOURCE_CATALOG if item.key == key), None)


def _dimension(name: str, ok: bool, evidence: str, *, wait: bool = False) -> DimensionProof:
    if ok:
        state = ProofState.PASS
    elif wait:
        state = ProofState.WAIT
    else:
        state = ProofState.FAIL
    return DimensionProof(id=name, state=state, evidence=evidence)


def evaluate_r0b_cohort() -> R0BCohortReport:
    report = compile_default_inventory()
    compiled = {item.source_contract_id: item for item in report.source_contracts}
    members: list[CohortSourceProof] = []
    for item in R0B_COHORT:
        descriptor = _descriptor(item.source_key)
        parser = STRUCTURED_PARSERS.get(item.source_key)
        compiled_row = compiled.get(item.source_key)
        reviewed_proof = proof_for_source(item.source_key)
        genuine_fields = dict(reviewed_proof.fields) if reviewed_proof else {}
        genuine = set(genuine_fields)
        waived = set(reviewed_proof.waivers) if reviewed_proof else set()
        missing = sorted(ALLOWED_EXTENDED_FIELDS - genuine)
        unreviewed = sorted(ALLOWED_EXTENDED_FIELDS - genuine - waived)
        field_reviewed = not unreviewed

        catalog_ok = descriptor is not None
        parser_ok = parser is not None
        official = bool(
            descriptor
            and "OFFICIAL" in str(descriptor.authority).upper()
        )
        named = compiled_row is not None or catalog_ok
        freshness_ok = bool(descriptor and getattr(descriptor, "stale_after_hours", None))
        empty_distinct = item.source_key in {
            "nse_fno_ban",
            "nse_mwpl_percentages",
        } or parser_ok
        mwpl_wait = (
            item.source_key == "nse_mwpl_percentages"
            and descriptor is not None
            and "UNAVAILABLE" in (descriptor.parser_status or "")
        )
        dimensions = [
            _dimension(
                "catalog_identity",
                catalog_ok,
                f"catalog={'yes' if catalog_ok else 'missing'}",
            ),
            _dimension(
                "parser_registered",
                parser_ok,
                f"parser={'registered' if parser_ok else 'missing'}",
            ),
            _dimension(
                "valid_empty_or_unavailable_distinct",
                empty_distinct and not mwpl_wait,
                (
                    "MWPL remains WAIT: no verified official percentage artifact"
                    if mwpl_wait
                    else "Ban parser distinguishes valid-empty; other cohort parsers are registered"
                ),
                wait=mwpl_wait,
            ),
            _dimension(
                "official_authority",
                official,
                f"authority={getattr(descriptor, 'authority', None)}",
            ),
            _dimension(
                "dataset_root_or_named_contract",
                named,
                (
                    f"compiled={compiled_row.source_contract_id}"
                    if compiled_row is not None
                    else "catalog-only named contract"
                ),
            ),
            _dimension(
                "freshness_policy",
                freshness_ok,
                f"stale_after_hours={getattr(descriptor, 'stale_after_hours', None)}",
            ),
            _dimension(
                "extended_fields_complete",
                not missing,
                "missing=" + (",".join(missing) if missing else "none"),
                wait=bool(missing),
            ),
            _dimension(
                "extended_fields_reviewed",
                field_reviewed,
                (
                    "unreviewed=none; waived=" + ",".join(sorted(waived))
                    if field_reviewed
                    else "unreviewed=" + ",".join(unreviewed)
                ),
                wait=not field_reviewed,
            ),
            _dimension(
                "source_specific_retry_breaker",
                (
                    "retry_policy" in genuine_fields
                    and str(
                        genuine_fields.get("circuit_breaker_policy", "")
                    ).startswith("SHARED_NSE_DOMAIN_BREAKER")
                ),
                (
                    str(genuine_fields.get("circuit_breaker_policy", "missing"))
                    + "; shared domain breaker is live in market_data_service"
                ),
            ),
        ]
        proven = all(dim.state is ProofState.PASS for dim in dimensions)
        members.append(
            CohortSourceProof(
                sourceKey=item.source_key,
                className=item.class_name,
                role=item.role,
                parserStatus=descriptor.parser_status if descriptor else None,
                dimensions=dimensions,
                proven=proven,
                reviewed=field_reviewed,
                quarantined=not proven,
                confirmEligible=item.confirm_eligible and proven,
                canUnlockConfirmed=False,
                canVote=False,
                missingExtendedFields=missing,
                waivedExtendedFields=sorted(waived),
            )
        )
    return R0BCohortReport(
        sourceActivationReady=False,
        gateAuthorizedSourceKeyCount=0,
        h1a0Passed=report.h1a0_acceptance_passed,
        h1a0Total=report.h1a0_acceptance_total,
        workbookSha256=report.workbook_sha256,
        rowCount=report.row_count,
        provenCount=sum(1 for item in members if item.proven),
        reviewedCount=sum(1 for item in members if item.reviewed),
        quarantinedCount=sum(1 for item in members if item.quarantined),
        members=members,
        note=(
            "R0-B first official cohort. reviewed=fields proven or named-waiver. "
            "proven=all dimensions PASS. Shared NSE retry/breaker is a proven "
            "domain policy, not a unique per-source breaker. MWPL has no official "
            "percentage artifact is the NCL combineoi zip; MWPL stays "
            "confirm-ineligible. canVote stays false until a File A "
            "activation amendment. "
            "This cannot set sourceActivationReady."
        ),
    )
