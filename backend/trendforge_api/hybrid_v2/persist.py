"""Optional overlay persistence. GET computes from the latest spine, like s4s5."""

from __future__ import annotations

from ..selection.store import latest_selection_payload, persist_selection_payload
from .contracts import PROFILE_ID, HybridOverlayBatchV1


def persist_overlay(batch: HybridOverlayBatchV1) -> HybridOverlayBatchV1:
    persist_selection_payload(
        run_id=f"{PROFILE_ID}:{batch.trading_date}:{batch.row_count}",
        profile_id=PROFILE_ID,
        as_of=batch.decision_at,
        payload=batch.model_dump(mode="json", by_alias=True),
        candidates=tuple(
            (
                f"hybrid-{row.symbol}",
                row.symbol,
                row.research_state.value,
                row.model_dump(mode="json", by_alias=True),
            )
            for row in batch.rows
        ),
    )
    return batch


def latest_overlay() -> HybridOverlayBatchV1 | None:
    payload = latest_selection_payload(PROFILE_ID)
    return HybridOverlayBatchV1.model_validate(payload) if payload is not None else None
