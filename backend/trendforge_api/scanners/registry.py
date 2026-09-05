"""File A R8 native core scanner registry (STO-016 versioned definitions).

Five deterministic cores that WRAP the existing R5 closed-bar engine
(selection/structure.py FTR-006/007/017). They never fork a third structure
engine, never vote, and never emit CONFIRMED - public state stays S7/R2-B.

parameterHash = SHA256 of the sorted compact JSON parameters blob.
pkCompatible is a PARITY-FIXTURE marker only (PK_R4_NATIVE_MAP covers
FTR-005/006/007); it never grants a vote.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

SCANNER_ENGINE = "trendforge.numpy-pandas"
SCHEMA_VERSION = "trendforge.scanner-registry.v1"
MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)

Family = Literal["STRUCTURE", "PARTICIPATION"]


class ScannerDefinitionV1(BaseModel):
    model_config = MODEL_CONFIG

    scanner_id: str = Field(min_length=1)
    version: Literal["v1"] = "v1"
    engine: str = SCANNER_ENGINE
    parameters_json: str = Field(alias="parametersJson")
    parameter_hash: str = Field(alias="parameterHash")
    min_bars: int = Field(ge=1, alias="minBars")
    family: Family
    group: str = Field(min_length=1)
    authority: Literal["NATIVE"] = "NATIVE"
    can_support_confirmed: Literal[False] = False
    pk_compatible: bool = False
    guidance_label: str
    display_priority: int = Field(default=100, ge=1, alias="displayPriority")

    @model_validator(mode="after")
    def hash_matches_parameters(self) -> "ScannerDefinitionV1":
        digest = hashlib.sha256(self.parameters_json.encode("utf-8")).hexdigest()
        if digest != self.parameter_hash:
            raise ValueError("parameterHash does not match parametersJson")
        return self


def _definition(
    scanner_id: str,
    *,
    parameters: dict,
    min_bars: int,
    family: Family,
    group: str,
    guidance_label: str,
    pk_compatible: bool,
    display_priority: int,
) -> ScannerDefinitionV1:
    parameters_json = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
    return ScannerDefinitionV1(
        scannerId=scanner_id,
        parametersJson=parameters_json,
        parameterHash=hashlib.sha256(parameters_json.encode("utf-8")).hexdigest(),
        minBars=min_bars,
        family=family,
        group=group,
        guidanceLabel=guidance_label,
        pkCompatible=pk_compatible,
        displayPriority=display_priority,
    )


# Detection source per scanner: R5 claims by feature id. Twin scanners share
# the same claim and correlation group; representative selection is
# first-wins in registry order (FUS-009).
_SCANNER_SPECS: tuple[dict, ...] = (
    {
        "id": "native.breakout.v1",
        "params": {"featureId": "FTR-006", "signal": "rangeAcceptance"},
        "min_bars": 22,
        "family": "STRUCTURE",
        "group": "CG_PRICE_STRUCTURE",
        "label": "Breakout matched - guidance",
        "pk": True,
        "display_priority": 10,
    },
    {
        "id": "native.trend.v1",
        "params": {"featureId": "FTR-006", "signal": "trendContinuation"},
        "min_bars": 22,
        "family": "STRUCTURE",
        "group": "CG_PRICE_STRUCTURE",
        "label": "Trend continuation matched - guidance",
        "pk": True,
        "display_priority": 20,
    },
    {
        "id": "native.nr_compression.v1",
        "params": {"featureId": "FTR-007", "signal": "narrowRange"},
        "min_bars": 8,
        "family": "STRUCTURE",
        "group": "CG_COMPRESSION",
        "label": "Compression - max WATCH unless S7",
        "pk": True,
        "display_priority": 30,
    },
    {
        "id": "native.rvol.v1",
        "params": {"featureId": "FTR-017", "signal": "rvolEod", "baselineBars": 20},
        "min_bars": 21,
        "family": "PARTICIPATION",
        "group": "CG_ACTIVITY_SESSION",
        "label": "RVOL matched - guidance",
        "pk": False,
        "display_priority": 10,
    },
    {
        "id": "native.volume_thrust.v1",
        "params": {
            "featureId": "FTR-017",
            "signal": "volumeThrust",
            "baselineRvol": 1.5,
            "multiplier": 2.0,
        },
        "min_bars": 21,
        "family": "PARTICIPATION",
        "group": "CG_ACTIVITY_SESSION",
        "label": "Volume thrust - same session vote as RVOL",
        "pk": False,
        "display_priority": 20,
    },
    # ---- R13 bounded families (chips-only; no upstream claims minted) ----
    {
        "id": "native.vcp.v1",
        "params": {
            "featureId": "FTR-008",
            "signal": "volatilityContraction",
            "lookbackBars": 60,
            "pivotRadius": 2,
            "contractions": 3,
            "volumeDryUpRatio": 0.70,
            "rangeSource": "adjustedOHLC",
        },
        "min_bars": 61,
        "family": "STRUCTURE",
        "group": "CG_COMPRESSION",
        "label": "VCP - trade guidance, not an order",
        "pk": False,
        "display_priority": 10,
    },
    {
        "id": "native.ttm_squeeze.v1",
        "params": {
            "featureId": "FTR-009",
            "signal": "ttmSqueeze",
            "bbPeriod": 20,
            "bbStd": 2.0,
            "bbMid": "SMA",
            "kcPeriod": 20,
            "kcAtrPeriod": 10,
            "kcMultiplier": 1.5,
            "kcMid": "EMA",
            "atrSource": "trueRange",
        },
        "min_bars": 31,
        "family": "STRUCTURE",
        "group": "CG_COMPRESSION",
        "label": "TTM squeeze - trade guidance, not an order",
        "pk": False,
        "display_priority": 20,
    },
    {
        "id": "native.trend_overlay.v1",
        "params": {
            "featureId": "FTR-012",
            "signal": "smaRelation",
            "fast": 20,
            "slow": 50,
        },
        "min_bars": 51,
        "family": "STRUCTURE",
        "group": "CG_TREND_OVERLAYS",
        "label": "Trend overlay context - guidance",
        "pk": False,
        "display_priority": 10,
    },
    {
        "id": "native.momentum.v1",
        "params": {
            "featureId": "FTR-013",
            "signal": "rsiCondition",
            "oscillator": "RSI",
            "period": 14,
            "threshold": 50,
            "method": "Wilder",
        },
        "min_bars": 15,
        "family": "STRUCTURE",
        "group": "CG_MOMENTUM_OSCILLATORS",
        "label": "Momentum condition - guidance",
        "pk": False,
        "display_priority": 10,
    },
    {
        "id": "native.reversal.v1",
        "params": {
            "featureId": "FTR-014",
            "signal": "failedBreakReversal",
            "reclaimWindow": 3,
            "scanWindow": 10,
        },
        "min_bars": 12,
        "family": "STRUCTURE",
        "group": "CG_REVERSAL",
        "label": "Reversal reclaim - guidance",
        "pk": False,
        "display_priority": 10,
    },
    {
        "id": "native.extremes.v1",
        "params": {
            "featureId": "FTR-015",
            "signal": "pitExtremes",
            "d10": 10,
            "w52": 252,
        },
        "min_bars": 11,
        "family": "STRUCTURE",
        "group": "CG_PRICE_STRUCTURE",
        "label": "10d/52w extreme - trade guidance, not an order",
        "pk": False,
        "display_priority": 30,
    },
)

NATIVE_CORE_IDS: tuple[str, ...] = tuple(spec["id"] for spec in _SCANNER_SPECS)


def scanner_definition(scanner_id: str) -> ScannerDefinitionV1:
    spec = next((s for s in _SCANNER_SPECS if s["id"] == scanner_id), None)
    if spec is None:
        raise KeyError(f"unknown native scanner: {scanner_id}")
    return _definition(
        spec["id"],
        parameters=spec["params"],
        min_bars=spec["min_bars"],
        family=spec["family"],  # type: ignore[arg-type]
        group=spec["group"],
        guidance_label=spec["label"],
        pk_compatible=spec["pk"],
        display_priority=spec["display_priority"],
    )


NATIVE_CORE_DEFINITIONS: tuple[ScannerDefinitionV1, ...] = tuple(
    scanner_definition(scanner_id) for scanner_id in NATIVE_CORE_IDS
)

__all__ = [
    "NATIVE_CORE_DEFINITIONS",
    "NATIVE_CORE_IDS",
    "SCANNER_ENGINE",
    "SCHEMA_VERSION",
    "ScannerDefinitionV1",
    "scanner_definition",
]
