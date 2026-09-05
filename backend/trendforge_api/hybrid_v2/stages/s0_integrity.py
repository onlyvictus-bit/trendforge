"""S0 integrity + freshness for the overlay. WAIT_STALE on staleness."""

from __future__ import annotations

from ..as_lab.delivery import AsDeliveryEvidenceV1


def assess_integrity(
    *,
    structure_present: bool,
    as_evidence: AsDeliveryEvidenceV1,
) -> tuple[str, tuple[str, ...]]:
    codes: list[str] = []
    if not structure_present:
        codes.append("WAIT_R5_NOT_PERSISTED")
    if as_evidence.status == "STALE":
        codes.append("WAIT_STALE_MTO_NOT_SESSION")
    status = "WAIT_STALE" if codes else "OK"
    return status, tuple(codes)
