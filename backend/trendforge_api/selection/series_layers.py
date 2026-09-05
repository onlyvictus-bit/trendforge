"""CROSS-020: raw market series stay immutable; CA opens a new adjusted version."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import stable_id


class SeriesKind(StrEnum):
    RAW = "RAW"
    ADJUSTED = "ADJUSTED"


@dataclass(frozen=True)
class MarketSeriesRef:
    series_id: str
    kind: SeriesKind
    version: str
    source_artifact_hash: str
    adjustment_event_id: str | None = None


def raw_series(*, instrument_key: str, artifact_hash: str) -> MarketSeriesRef:
    return MarketSeriesRef(
        series_id=stable_id("raw", instrument_key, artifact_hash),
        kind=SeriesKind.RAW,
        version="raw-1",
        source_artifact_hash=artifact_hash,
        adjustment_event_id=None,
    )


def open_adjusted_series(
    raw: MarketSeriesRef, *, adjustment_event_id: str
) -> MarketSeriesRef:
    if raw.kind is not SeriesKind.RAW:
        raise ValueError("adjustments must start from a RAW series")
    if not adjustment_event_id.strip():
        raise ValueError("adjustment event id is required")
    return MarketSeriesRef(
        series_id=stable_id("adj", raw.series_id, adjustment_event_id),
        kind=SeriesKind.ADJUSTED,
        version=f"adj-{adjustment_event_id}",
        source_artifact_hash=raw.source_artifact_hash,
        adjustment_event_id=adjustment_event_id,
    )
