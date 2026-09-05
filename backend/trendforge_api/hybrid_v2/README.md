# Hybrid V2 overlay (paper research package)

Ceiling: `RESEARCH_PROXY_NOT_CALIBRATED`. Not File A. Not R2-B. Not CONFIRMED. Not size.

- Reads the live spine read-only: R1 bundle, R2-A attention, R4 pin, R14 ca-join, R5 structure.
- Phase-2 real work only: AS delivery (`nse_mto_delivery` last-good), triple-barrier label
  spec, cost-aware `p_min` / Kelly illustration.
- B1/B2/B4/B5 and S6 stay UNKNOWN (`UNKNOWN_NEEDS_R12`) until their own File A joins exist.
- Both S4/S5 families are kept; the adopted split (WITHOUT) is default display, WITH kept for A/B.
- Cannot unlock CONFIRMED, cannot set qty, cannot write R1/R2/R4/R14/R5.

Schema: `trendforge.hybrid-v2-overlay.v1`. Profile: `PRF-HYBRID-V2-OVERLAY`.
API: `GET /api/v1/hybrid-v2/overlay`, `GET /api/v1/hybrid-v2/overlay/{symbol}`. POST -> 405.
