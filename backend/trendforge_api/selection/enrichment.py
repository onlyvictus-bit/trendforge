from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .contracts import InstrumentIdentity, MODEL_CONFIG, SelectionState


class EnrichmentJob(StrEnum):
    OPTION_CHAIN = "OPTION_CHAIN"
    DERIVATIVES_OI = "DERIVATIVES_OI"
    CORPORATE_EVENTS = "CORPORATE_EVENTS"
    DELIVERY = "DELIVERY"
    MCX_CONTRACT = "MCX_CONTRACT"


class EnrichmentCandidate(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str = Field(min_length=1)
    instrument: InstrumentIdentity
    state: SelectionState
    discovery_priority: float = Field(ge=0, le=1)
    requested_jobs: tuple[EnrichmentJob, ...]

    @model_validator(mode="after")
    def require_unique_jobs(self) -> "EnrichmentCandidate":
        if len(set(self.requested_jobs)) != len(self.requested_jobs):
            raise ValueError("requested enrichment jobs must be unique")
        return self


class EnrichmentBudget(BaseModel):
    model_config = MODEL_CONFIG

    budget_id: str = Field(min_length=1)
    budget_version: str = Field(min_length=1)
    max_candidates: int = Field(ge=1, le=100)
    max_jobs_per_candidate: int = Field(ge=1, le=10)
    allowed_jobs: tuple[EnrichmentJob, ...]

    @model_validator(mode="after")
    def require_allowed_jobs(self) -> "EnrichmentBudget":
        if not self.allowed_jobs:
            raise ValueError("enrichment budget needs at least one allowed job")
        if len(set(self.allowed_jobs)) != len(self.allowed_jobs):
            raise ValueError("allowed jobs must be unique")
        return self


class EnrichmentAssignment(BaseModel):
    model_config = MODEL_CONFIG

    candidate_id: str
    instrument_id: str
    queue_rank: int = Field(ge=1)
    jobs: tuple[EnrichmentJob, ...]


class EnrichmentPlan(BaseModel):
    model_config = MODEL_CONFIG

    budget: EnrichmentBudget
    assignments: tuple[EnrichmentAssignment, ...]
    excluded_candidate_ids: tuple[str, ...]
    input_count: int = Field(ge=0)

    @property
    def selected_count(self) -> int:
        return len(self.assignments)


def build_enrichment_plan(
    *,
    candidates: tuple[EnrichmentCandidate, ...],
    budget: EnrichmentBudget,
) -> EnrichmentPlan:
    """Create a bounded expensive-job queue; queue rank is not evidence."""

    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate_id values must be unique")

    state_order = {
        SelectionState.WAIT: 0,
        SelectionState.WATCH: 1,
        SelectionState.CONFIRMED: 2,
        SelectionState.REJECT: 3,
    }
    allowed = set(budget.allowed_jobs)
    eligible = [
        (
            candidate,
            tuple(job for job in candidate.requested_jobs if job in allowed)[
                : budget.max_jobs_per_candidate
            ],
        )
        for candidate in candidates
        if candidate.state in {SelectionState.WATCH, SelectionState.WAIT}
        and any(job in allowed for job in candidate.requested_jobs)
    ]
    ranked = sorted(
        eligible,
        key=lambda item: (
            state_order[item[0].state],
            -item[0].discovery_priority,
            item[0].candidate_id,
        ),
    )
    selected = ranked[: budget.max_candidates]
    assignments = tuple(
        EnrichmentAssignment(
            candidate_id=candidate.candidate_id,
            instrument_id=candidate.instrument.instrument_id,
            queue_rank=index,
            jobs=jobs,
        )
        for index, (candidate, jobs) in enumerate(selected, start=1)
    )
    assigned_ids = {assignment.candidate_id for assignment in assignments}
    excluded = tuple(
        sorted(
            candidate.candidate_id
            for candidate in candidates
            if candidate.candidate_id not in assigned_ids
        )
    )
    return EnrichmentPlan(
        budget=budget,
        assignments=assignments,
        excluded_candidate_ids=excluded,
        input_count=len(candidates),
    )
