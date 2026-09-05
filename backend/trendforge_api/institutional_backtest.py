from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class WalkForwardModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WalkForwardPoint(WalkForwardModel):
    as_of: datetime
    factor_score: float
    forward_return: float

    @field_validator("as_of")
    @classmethod
    def as_of_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class WalkForwardPrediction(WalkForwardModel):
    as_of: datetime
    training_end: datetime
    factor_score: float
    predicted_direction: int
    forward_return: float
    won: bool


class WalkForwardReport(WalkForwardModel):
    observation_count: int
    evaluation_count: int
    win_rate: float = Field(ge=0, le=1)
    average_forward_return: float
    expectancy: float
    lookahead_detected: bool
    predictions: list[WalkForwardPrediction]


def walk_forward_validate(
    points: list[WalkForwardPoint],
    *,
    min_train_size: int = 60,
    signal_threshold: float = 1.5,
) -> WalkForwardReport:
    if min_train_size < 2:
        raise ValueError("min_train_size must be at least 2")
    ordered = sorted(points, key=lambda item: item.as_of)
    if len({item.as_of for item in ordered}) != len(ordered):
        raise ValueError("walk-forward timestamps must be unique")
    predictions: list[WalkForwardPrediction] = []
    for index in range(min_train_size, len(ordered)):
        current = ordered[index]
        training_end = ordered[index - 1].as_of
        direction = (
            1
            if current.factor_score >= signal_threshold
            else -1
            if current.factor_score <= -signal_threshold
            else 0
        )
        if direction == 0:
            won = False
        else:
            won = (direction * current.forward_return) > 0
        predictions.append(
            WalkForwardPrediction(
                as_of=current.as_of,
                training_end=training_end,
                factor_score=current.factor_score,
                predicted_direction=direction,
                forward_return=current.forward_return,
                won=won,
            )
        )
    evaluated = [row for row in predictions if row.predicted_direction != 0]
    wins = sum(row.won for row in evaluated)
    signed_returns = [row.predicted_direction * row.forward_return for row in evaluated]
    return WalkForwardReport(
        observation_count=len(ordered),
        evaluation_count=len(predictions),
        win_rate=wins / len(evaluated) if evaluated else 0.0,
        average_forward_return=(
            sum(row.forward_return for row in predictions) / len(predictions)
            if predictions
            else 0.0
        ),
        expectancy=sum(signed_returns) / len(signed_returns) if signed_returns else 0.0,
        lookahead_detected=any(row.training_end >= row.as_of for row in predictions),
        predictions=predictions,
    )
