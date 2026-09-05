"""Production-facing R18 orchestration over immutable R16 and R18 storage."""

from __future__ import annotations

from typing import Any

from .r16_store import list_dataset_runs, r16_schema_status
from .r18_governance import (
    ChallengerEvaluationInputV1,
    ChallengerEvaluationV1,
    evaluate_challenger,
)
from .r18_store import persist_evaluation, persist_manifest, schema_status


def _require_r16_dataset(dataset_hash: str) -> dict[str, Any]:
    if not r16_schema_status()["applied"]:
        raise RuntimeError("WAIT_R16_SCHEMA_NOT_APPLIED")
    for row in list_dataset_runs(limit=500000):
        if row.get("datasetRevisionHash") == dataset_hash:
            return row
    raise ValueError("R16_PIT_DATASET_HASH_NOT_FOUND")


def run_offline_challenger_evaluation(
    payload: ChallengerEvaluationInputV1,
) -> ChallengerEvaluationV1:
    """Evaluate and persist only after the referenced R16 dataset is proven."""

    if not schema_status()["applied"]:
        raise RuntimeError("WAIT_R18_SCHEMA_NOT_APPLIED")
    dataset = _require_r16_dataset(payload.dataset_hash)
    if dataset.get("datasetStatus") not in {"BUILDING", "PIT_READY", "PIT_APPROVED"}:
        raise ValueError("R16_PIT_DATASET_STATUS_INVALID")
    evaluation = evaluate_challenger(payload)
    persist_manifest(payload.manifest.model_dump(mode="json", by_alias=True))
    persist_evaluation(evaluation.model_dump(mode="json", by_alias=True))
    return evaluation
