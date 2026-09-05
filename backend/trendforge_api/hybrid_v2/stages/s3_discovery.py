"""S3 discovery stage. Pass-through of the R2 display_order shortlist."""

from __future__ import annotations

from ...selection.attention_order import AttentionRowV1


def discovery_rank(attention_row: AttentionRowV1) -> int:
    return attention_row.display_order
