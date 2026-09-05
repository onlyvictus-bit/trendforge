"""S9 attribution schema. Empty until triple-barrier labels persist."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

MODEL_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class AttributionSchemaV1(BaseModel):
    """MFE/MAE, calibration drift and slippage drift fields for later S9 use.

    No values are produced in this milestone: labels do not exist yet, so every
    field stays None. This is a schema commitment, not an attribution claim.
    """

    model_config = MODEL_CONFIG

    symbol: str
    mfe_r: None = None
    mae_r: None = None
    predicted_p: None = None
    realised_p: None = None
    assumed_slippage: None = None
    realised_slippage: None = None
    labels_persisted: bool = Field(default=False)
