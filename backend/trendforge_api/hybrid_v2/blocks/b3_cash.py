"""B3 cash-market conviction. Phase-2 real module: official AS delivery z.

The adopted split puts B1-B3 inside p-hat; today only B3 has a real input and
only when the official MTO last-good is USABLE for the research session.
"""

from __future__ import annotations

from ..as_lab.delivery import AsDeliveryEvidenceV1

B3_WHY_UNKNOWN = ("B3_WAIT_AS_DELIVERY_USABLE",)


def b3_z(evidence: AsDeliveryEvidenceV1) -> float | None:
    if evidence.status == "USABLE":
        return evidence.delivery_z
    return None
