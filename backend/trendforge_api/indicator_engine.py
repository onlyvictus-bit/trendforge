from __future__ import annotations

from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from math import isclose, isfinite

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


MODEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    frozen=True,
)

INDICATOR_ENGINE_ID = "trendforge.numpy-pandas"
INDICATOR_ENGINE_VERSION = "1.0.0"
PINNED_NUMPY_VERSION = "2.4.3"
PINNED_PANDAS_VERSION = "2.3.3"
DEFAULT_ABSOLUTE_TOLERANCE = 1e-10
DEFAULT_RELATIVE_TOLERANCE = 1e-8


class IndicatorInputState(StrEnum):
    OK = "OK"
    INPUT_INCOMPLETE = "INPUT_INCOMPLETE"
    ENGINE_MISMATCH = "ENGINE_MISMATCH"
    REGISTRY_MISMATCH = "REGISTRY_MISMATCH"


class IndicatorEnginePin(BaseModel):
    model_config = MODEL_CONFIG

    engine_id: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    implementation_owner: str = Field(min_length=1)
    numpy_version: str = Field(min_length=1)
    pandas_version: str = Field(min_length=1)
    license_summary: str = Field(min_length=1)
    warmup_policy: str = Field(min_length=1)
    parity_policy: str = Field(min_length=1)
    absolute_tolerance: float = Field(ge=0)
    relative_tolerance: float = Field(ge=0)


class RuntimeEngineCheck(BaseModel):
    model_config = MODEL_CONFIG

    ok: bool
    engine_id: str
    engine_version: str
    expected_packages: dict[str, str]
    observed_packages: dict[str, str | None]
    errors: tuple[str, ...] = ()


class IndicatorBinding(BaseModel):
    model_config = MODEL_CONFIG

    feature_id: str = Field(pattern=r"^FTR-\d{3}$")
    feature_version: str = Field(min_length=1)
    engine_id: str | None = None
    engine_version: str | None = None
    minimum_warmup_bars: int = Field(ge=0)
    observation_count: int = Field(ge=0)

    @model_validator(mode="after")
    def require_complete_engine_identity(self) -> "IndicatorBinding":
        if (self.engine_id is None) != (self.engine_version is None):
            raise ValueError(
                "indicator engine ID and version must be supplied together"
            )
        return self


class IndicatorManifestCheck(BaseModel):
    model_config = MODEL_CONFIG

    ok: bool
    state: IndicatorInputState
    engine_id: str
    engine_version: str
    feature_ids: tuple[str, ...]
    errors: tuple[str, ...] = ()
    can_emit_indicator_claims: bool = False


class IndicatorParityCheck(BaseModel):
    model_config = MODEL_CONFIG

    ok: bool
    state: str
    compared_count: int = Field(ge=0)
    max_absolute_error: float | None = Field(default=None, ge=0)
    max_relative_error: float | None = Field(default=None, ge=0)
    divergent_keys: tuple[str, ...] = ()
    absolute_tolerance: float = Field(ge=0)
    relative_tolerance: float = Field(ge=0)


def pinned_indicator_engine() -> IndicatorEnginePin:
    return IndicatorEnginePin(
        engine_id=INDICATOR_ENGINE_ID,
        engine_version=INDICATOR_ENGINE_VERSION,
        implementation_owner="trendforge_api indicator calculations",
        numpy_version=PINNED_NUMPY_VERSION,
        pandas_version=PINNED_PANDAS_VERSION,
        license_summary="NumPy and pandas are BSD-3-Clause runtime dependencies.",
        warmup_policy=(
            "Each feature contract declares minimum_warmup_bars. Insufficient "
            "history returns INPUT_INCOMPLETE and cannot emit an indicator claim."
        ),
        parity_policy=(
            "Offline reference comparisons use versioned fixtures and record "
            "PARITY_DIVERGENCE outside configured absolute/relative tolerances."
        ),
        absolute_tolerance=DEFAULT_ABSOLUTE_TOLERANCE,
        relative_tolerance=DEFAULT_RELATIVE_TOLERANCE,
    )


def verify_indicator_runtime() -> RuntimeEngineCheck:
    expected = {
        "numpy": PINNED_NUMPY_VERSION,
        "pandas": PINNED_PANDAS_VERSION,
    }
    observed: dict[str, str | None] = {}
    errors: list[str] = []
    for package, expected_version in expected.items():
        try:
            observed_version = version(package)
        except PackageNotFoundError:
            observed_version = None
        observed[package] = observed_version
        if observed_version != expected_version:
            errors.append(
                f"{package} expected {expected_version}, observed {observed_version or 'MISSING'}"
            )
    return RuntimeEngineCheck(
        ok=not errors,
        engine_id=INDICATOR_ENGINE_ID,
        engine_version=INDICATOR_ENGINE_VERSION,
        expected_packages=expected,
        observed_packages=observed,
        errors=tuple(errors),
    )


def assess_indicator_manifest(
    bindings: tuple[IndicatorBinding, ...],
) -> IndicatorManifestCheck:
    from .feature_registry import feature_contract_by_id

    errors: list[str] = []
    if not bindings:
        errors.append("indicator manifest has no feature bindings")
        return IndicatorManifestCheck(
            ok=False,
            state=IndicatorInputState.ENGINE_MISMATCH,
            engine_id=INDICATOR_ENGINE_ID,
            engine_version=INDICATOR_ENGINE_VERSION,
            feature_ids=(),
            errors=tuple(errors),
        )

    feature_ids = tuple(binding.feature_id for binding in bindings)
    if len(set(feature_ids)) != len(feature_ids):
        errors.append("indicator manifest contains duplicate feature IDs")

    engines = {
        (binding.engine_id, binding.engine_version)
        for binding in bindings
        if binding.engine_id is not None and binding.engine_version is not None
    }
    if any(binding.engine_id is None for binding in bindings):
        errors.append("indicator manifest contains a missing engine identity")
    if len(engines) > 1:
        errors.append("indicator manifest mixes multiple engine identities")
    if engines and engines != {(INDICATOR_ENGINE_ID, INDICATOR_ENGINE_VERSION)}:
        errors.append("indicator manifest does not match the pinned TrendForge engine")

    contracts = {}
    for binding in bindings:
        contract = feature_contract_by_id(binding.feature_id)
        if contract is None:
            errors.append(f"{binding.feature_id} is not registered")
            continue
        contracts[binding.feature_id] = contract
        if binding.feature_version != contract.feature_version:
            errors.append(
                f"{binding.feature_id} feature version {binding.feature_version} does not "
                f"match registry {contract.feature_version}"
            )
        if contract.indicator_engine_id is None:
            errors.append(f"{binding.feature_id} is not an indicator-backed feature")
        elif (
            binding.engine_id != contract.indicator_engine_id
            or binding.engine_version != contract.indicator_engine_version
        ):
            errors.append(
                f"{binding.feature_id} engine identity does not match registry"
            )
        if binding.minimum_warmup_bars != contract.minimum_warmup_bars:
            errors.append(
                f"{binding.feature_id} warm-up {binding.minimum_warmup_bars} does not "
                f"match registry {contract.minimum_warmup_bars}"
            )

    warmup_errors = [
        (
            f"{binding.feature_id} requires "
            f"{contracts[binding.feature_id].minimum_warmup_bars} bars, "
            f"observed {binding.observation_count}"
        )
        for binding in bindings
        if binding.feature_id in contracts
        and binding.observation_count
        < contracts[binding.feature_id].minimum_warmup_bars
    ]
    errors.extend(warmup_errors)

    runtime = verify_indicator_runtime()
    if not runtime.ok:
        errors.extend(runtime.errors)

    engine_error = any(
        "engine" in error or "numpy" in error or "pandas" in error for error in errors
    )
    registry_error = any(
        "not registered" in error
        or "does not match registry" in error
        or "feature version" in error
        or "not an indicator-backed feature" in error
        for error in errors
    )
    state = (
        IndicatorInputState.ENGINE_MISMATCH
        if engine_error
        else (
            IndicatorInputState.REGISTRY_MISMATCH
            if registry_error
            else (
                IndicatorInputState.INPUT_INCOMPLETE
                if warmup_errors
                else (
                    IndicatorInputState.REGISTRY_MISMATCH
                    if errors
                    else IndicatorInputState.OK
                )
            )
        )
    )
    return IndicatorManifestCheck(
        ok=not errors,
        state=state,
        engine_id=INDICATOR_ENGINE_ID,
        engine_version=INDICATOR_ENGINE_VERSION,
        feature_ids=feature_ids,
        errors=tuple(errors),
        can_emit_indicator_claims=not errors,
    )


def compare_indicator_parity(
    observed: dict[str, float | None],
    reference: dict[str, float | None],
    *,
    absolute_tolerance: float = DEFAULT_ABSOLUTE_TOLERANCE,
    relative_tolerance: float = DEFAULT_RELATIVE_TOLERANCE,
) -> IndicatorParityCheck:
    if absolute_tolerance < 0 or relative_tolerance < 0:
        raise ValueError("parity tolerances cannot be negative")

    keys = sorted(set(observed) | set(reference))
    if not keys:
        return IndicatorParityCheck(
            ok=False,
            state="PARITY_INVALID",
            compared_count=0,
            divergent_keys=(),
            absolute_tolerance=absolute_tolerance,
            relative_tolerance=relative_tolerance,
        )
    divergent: list[str] = []
    absolute_errors: list[float] = []
    relative_errors: list[float] = []
    for key in keys:
        left = observed.get(key)
        right = reference.get(key)
        if left is None or right is None or not isfinite(left) or not isfinite(right):
            divergent.append(key)
            continue
        absolute_error = abs(left - right)
        denominator = max(abs(left), abs(right), absolute_tolerance or 1.0)
        relative_error = absolute_error / denominator
        absolute_errors.append(absolute_error)
        relative_errors.append(relative_error)
        if not isclose(
            left,
            right,
            abs_tol=absolute_tolerance,
            rel_tol=relative_tolerance,
        ):
            divergent.append(key)

    return IndicatorParityCheck(
        ok=not divergent,
        state="PARITY_OK" if not divergent else "PARITY_DIVERGENCE",
        compared_count=len(keys),
        max_absolute_error=max(absolute_errors, default=None),
        max_relative_error=max(relative_errors, default=None),
        divergent_keys=tuple(divergent),
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
    )
