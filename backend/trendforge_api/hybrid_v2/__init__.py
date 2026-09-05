"""Hybrid V2 paper research overlay. Not File A. Not R2-B. Not CONFIRMED.

Read-only consumer of the live spine (R1, R2-A, R4, R14, R5). Emits the
`trendforge.hybrid-v2-overlay.v1` batch at ceiling RESEARCH_PROXY_NOT_CALIBRATED.
It can never unlock CONFIRMED, never set qty, and never write into R5.
"""

SCHEMA_VERSION = "trendforge.hybrid-v2-overlay.v1"

__all__ = ["SCHEMA_VERSION"]
