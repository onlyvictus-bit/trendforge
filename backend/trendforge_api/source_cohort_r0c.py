"""R0-C remaining source-contract quarantine.

R0-C is derived from the pinned inventory compiler. It is not a second source
registry and cannot activate, vote, confirm, size, or execute.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from .source_cohort_r0b import R0B_COHORT
from .source_inventory_compiler import InventoryCompilerReport, compile_default_inventory


class R0CMember(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    source_contract_id: str = Field(alias="sourceContractId")
    dataset_root_id: str = Field(alias="datasetRootId")
    maturity_state: str = Field(alias="maturityState")
    contract_status: str = Field(alias="contractStatus")
    decision_jobs: list[str] = Field(alias="decisionJobs")
    missing_extended_fields: list[str] = Field(alias="missingExtendedFields")
    quarantine_reasons: list[str] = Field(alias="quarantineReasons")
    reviewed: bool = False
    quarantined: bool = True
    activation_eligible: bool = Field(default=False, alias="activationEligible")
    can_vote: bool = Field(default=False, alias="canVote")
    can_unlock_confirmed: bool = Field(default=False, alias="canUnlockConfirmed")
    gate_permission: bool = Field(default=False, alias="gatePermission")
    executable: bool = False


class R0CCohortReport(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

    version: str = "R0-C-v1"
    slice: str = "R0-C"
    workbook_sha256: str | None = Field(default=None, alias="workbookSha256")
    source_activation_ready: bool = Field(alias="sourceActivationReady")
    gate_authorized_source_key_count: int = Field(alias="gateAuthorizedSourceKeyCount")
    compiled_contract_count: int = Field(alias="compiledContractCount")
    r0b_compiled_count: int = Field(alias="r0bCompiledCount")
    r0c_contract_count: int = Field(alias="r0cContractCount")
    reviewed_count: int = Field(alias="reviewedCount")
    quarantined_count: int = Field(alias="quarantinedCount")
    partition_complete: bool = Field(alias="partitionComplete")
    members: list[R0CMember]
    note: str


def build_r0c_cohort(report: InventoryCompilerReport) -> R0CCohortReport:
    contracts = list(report.source_contracts)
    ids = [item.source_contract_id for item in contracts]
    if len(ids) != len(set(ids)):
        raise ValueError("R0-C cannot partition duplicate source contract IDs")

    r0b_ids = {item.source_key for item in R0B_COHORT}
    compiled_r0b_ids = set(ids) & r0b_ids
    remaining = [item for item in contracts if item.source_contract_id not in r0b_ids]
    unexpected_gate = [item.source_contract_id for item in remaining if item.gate_permission]
    if unexpected_gate:
        raise ValueError(
            "R0-C contract unexpectedly has gate permission: " + ",".join(unexpected_gate)
        )

    members = [
        R0CMember(
            sourceContractId=item.source_contract_id,
            datasetRootId=item.dataset_root_id,
            maturityState=item.maturity_state.value,
            contractStatus=item.contract_status,
            decisionJobs=item.decision_jobs,
            missingExtendedFields=item.missing_extended_fields,
            quarantineReasons=sorted(
                set(item.maturity_missing_prerequisites)
                | set(item.missing_extended_fields)
                | {"R0_C_UNREVIEWED_CONTRACT"}
            ),
        )
        for item in remaining
    ]
    if len(compiled_r0b_ids) + len(members) != len(contracts):
        raise ValueError("R0-B/R0-C compiler partition is incomplete")

    return R0CCohortReport(
        workbookSha256=report.workbook_sha256,
        sourceActivationReady=False,
        gateAuthorizedSourceKeyCount=0,
        compiledContractCount=len(contracts),
        r0bCompiledCount=len(compiled_r0b_ids),
        r0cContractCount=len(members),
        reviewedCount=0,
        quarantinedCount=len(members),
        partitionComplete=True,
        members=members,
        note=(
            "R0-C is the compiler-derived remainder outside R0-B. Every member "
            "stays unreviewed, quarantined, non-voting, non-confirming and non-executable."
        ),
    )


def evaluate_r0c_cohort() -> R0CCohortReport:
    return build_r0c_cohort(compile_default_inventory())
