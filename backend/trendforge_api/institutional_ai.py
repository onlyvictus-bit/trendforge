from __future__ import annotations

import importlib.util
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ModelState(StrEnum):
    READY = "READY"
    UNTRAINED = "UNTRAINED"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"


class ModelCapability(BaseModel):
    key: str
    implementation: str
    dependency: str
    dependency_available: bool
    state: ModelState
    can_unlock_ready: bool = False


class ProbabilityBlend(BaseModel):
    ready: bool
    probability: float | None = Field(default=None, ge=0, le=1)
    missing_models: list[str]
    contributions: dict[str, float]


class AnomalyAssessment(BaseModel):
    model_state: ModelState
    anomaly_score: float
    is_anomaly: bool


class ModelDependencyError(RuntimeError):
    pass


class IsolationForestAdapter:
    """Anomaly veto model; its output must never be treated as direction probability."""

    def __init__(self, *, contamination: float = 0.05, random_state: int = 42) -> None:
        if not 0 < contamination <= 0.5:
            raise ValueError("contamination must be in (0, 0.5]")
        self._contamination = contamination
        self._random_state = random_state
        self._model: Any | None = None
        self._feature_count = 0

    def fit(self, features: list[list[float]]) -> None:
        if len(features) < 20:
            raise ValueError("Isolation Forest requires at least 20 observations")
        feature_count = len(features[0]) if features else 0
        if feature_count == 0 or any(len(row) != feature_count for row in features):
            raise ValueError("Isolation Forest features must be a non-empty rectangle")
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError as exc:
            raise ModelDependencyError("scikit-learn is unavailable") from exc
        self._model = IsolationForest(
            contamination=self._contamination,
            random_state=self._random_state,
            n_estimators=200,
            n_jobs=1,
        ).fit(features)
        self._feature_count = feature_count

    def assess(self, features: list[float]) -> AnomalyAssessment:
        if self._model is None:
            raise RuntimeError("Isolation Forest is not trained")
        if len(features) != self._feature_count:
            raise ValueError("feature count differs from the trained model")
        score = float(self._model.decision_function([features])[0])
        prediction = int(self._model.predict([features])[0])
        return AnomalyAssessment(
            model_state=ModelState.READY,
            anomaly_score=score,
            is_anomaly=prediction == -1,
        )


class HMMRegimeAdapter:
    """Optional directional regime model with deterministic state-to-direction mapping."""

    def __init__(self, *, n_components: int = 4, random_state: int = 42) -> None:
        if n_components < 2:
            raise ValueError("HMM requires at least two states")
        self._n_components = n_components
        self._random_state = random_state
        self._model: Any | None = None
        self._bullish_states: set[int] = set()
        self._feature_count = 0

    def fit(self, features: list[list[float]]) -> None:
        if len(features) < max(50, self._n_components * 10):
            raise ValueError("HMM requires a larger chronological training sample")
        feature_count = len(features[0]) if features else 0
        if feature_count == 0 or any(len(row) != feature_count for row in features):
            raise ValueError("HMM features must be a non-empty rectangle")
        try:
            from hmmlearn.hmm import GaussianHMM
        except ImportError as exc:
            raise ModelDependencyError("hmmlearn is unavailable") from exc
        model = GaussianHMM(
            n_components=self._n_components,
            covariance_type="diag",
            n_iter=200,
            random_state=self._random_state,
        )
        model.fit(features)
        self._model = model
        self._feature_count = feature_count
        ranked = sorted(
            range(self._n_components), key=lambda index: model.means_[index][0]
        )
        self._bullish_states = set(ranked[len(ranked) // 2 :])

    def bullish_probability(self, features: list[float]) -> float:
        if self._model is None:
            raise RuntimeError("HMM is not trained")
        if len(features) != self._feature_count:
            raise ValueError("feature count differs from the trained model")
        probabilities = self._model.predict_proba([features])[0]
        return float(sum(probabilities[index] for index in self._bullish_states))


def _available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def model_capabilities() -> dict[str, ModelCapability]:
    definitions = {
        "hmm": ("Hidden Markov regime model", "hmmlearn", "hmmlearn"),
        "isolation_forest": (
            "IsolationForest anomaly detector",
            "scikit-learn",
            "sklearn",
        ),
        "random_forest": (
            "RandomForest probability model",
            "scikit-learn",
            "sklearn",
        ),
        "xgboost": ("Gradient boosted probability model", "xgboost", "xgboost"),
        "lstm": ("Sequence probability model", "tensorflow", "tensorflow"),
    }
    output: dict[str, ModelCapability] = {}
    for key, (implementation, dependency, module) in definitions.items():
        available = _available(module)
        output[key] = ModelCapability(
            key=key,
            implementation=implementation,
            dependency=dependency,
            dependency_available=available,
            state=ModelState.UNTRAINED if available else ModelState.DEPENDENCY_MISSING,
        )
    return output


def blend_probabilities(
    *,
    probabilities: dict[str, float],
    weights: dict[str, float],
    required_models: set[str],
) -> ProbabilityBlend:
    missing = sorted(required_models - probabilities.keys())
    if missing:
        return ProbabilityBlend(
            ready=False,
            probability=None,
            missing_models=missing,
            contributions={},
        )
    invalid = sorted(key for key in required_models if not 0 <= probabilities[key] <= 1)
    if invalid:
        return ProbabilityBlend(
            ready=False,
            probability=None,
            missing_models=invalid,
            contributions={},
        )
    total_weight = sum(weights.get(key, 0.0) for key in required_models)
    if total_weight <= 0:
        return ProbabilityBlend(
            ready=False,
            probability=None,
            missing_models=sorted(required_models),
            contributions={},
        )
    contributions = {
        key: probabilities[key] * weights.get(key, 0.0) / total_weight
        for key in sorted(required_models)
    }
    return ProbabilityBlend(
        ready=True,
        probability=sum(contributions.values()),
        missing_models=[],
        contributions=contributions,
    )
