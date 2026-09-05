from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import trendforge_api.feature_engineering as feature_engineering_module
import trendforge_api.institutional_features as institutional_features_module
from trendforge_api.feature_engineering import build_point_in_time_features
from trendforge_api.feature_registry import (
    EXPECTED_FEATURE_IDS,
    FEATURES,
    MANDATORY_FEATURE_FIELDS,
    build_feature_registry,
    lint_feature_contract_rows,
    lint_feature_registry,
)
from trendforge_api.indicator_engine import (
    INDICATOR_ENGINE_ID,
    INDICATOR_ENGINE_VERSION,
    IndicatorBinding,
    IndicatorInputState,
    RuntimeEngineCheck,
    assess_indicator_manifest,
    compare_indicator_parity,
    verify_indicator_runtime,
)
from trendforge_api.institutional_features import (
    INSTITUTIONAL_FEATURE_KEYS,
    INSTITUTIONAL_MINIMUM_WARMUP_BARS,
    build_institutional_features,
)
from trendforge_api.main import app
from trendforge_api.models import DataTrust, OHLCVCandle
from trendforge_api.selection.contracts import (
    DataMode,
    EvidenceClaim,
    EvidenceDirection,
    EvidenceFamily,
    SelectionScanRun,
    StateCeiling,
)
from trendforge_api.source_contracts import SourceRole


UTC = timezone.utc
AS_OF = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)


def _registry_rows() -> list[dict[str, object]]:
    return [feature.model_dump(mode="python") for feature in FEATURES]


def _ohlcv_candles(count: int) -> list[OHLCVCandle]:
    candles: list[OHLCVCandle] = []
    for index in range(count):
        close = 100.0 + index * 0.1
        timestamp = AS_OF + timedelta(days=index)
        candles.append(
            OHLCVCandle(
                symbol="TEST",
                timeframe="1d",
                source="synthetic",
                timestamp=timestamp.isoformat(),
                open=close - 0.2,
                high=close + 0.8,
                low=close - 0.9,
                close=close,
                volume=100_000 + index * 100,
                trustLevel=DataTrust.SYNTHETIC_TEST,
                fetchedAt=timestamp.isoformat(),
            )
        )
    return candles


def _institutional_candles(count: int) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for index in range(count):
        close = 100.0 + index * 0.1
        rows.append(
            {
                "timestamp": (AS_OF + timedelta(days=index)).isoformat(),
                "open": close - 0.2,
                "high": close + 0.8,
                "low": close - 0.9,
                "close": close,
                "volume": 100_000 + index * 100,
                "barState": "COMPLETE",
            }
        )
    return rows


def test_feature_registry_contains_all_40_unique_contracts() -> None:
    manifest = build_feature_registry()
    ids = [feature.feature_id for feature in manifest.features]

    assert len(ids) == 40
    assert len(set(ids)) == 40
    assert set(ids) == EXPECTED_FEATURE_IDS
    assert manifest.research_only is True
    assert manifest.can_unlock_confirmed is False


def test_every_registry_row_contains_all_22_mandatory_fields() -> None:
    assert len(MANDATORY_FEATURE_FIELDS) == 22
    for feature in FEATURES:
        row = feature.model_dump(mode="python")
        assert set(MANDATORY_FEATURE_FIELDS) <= row.keys()
        for key in MANDATORY_FEATURE_FIELDS:
            value = row[key]
            if isinstance(value, str):
                assert value.strip(), f"{feature.feature_id}.{key} is blank"
            if isinstance(value, tuple):
                assert value, f"{feature.feature_id}.{key} is empty"


def test_registry_lint_fails_when_a_mandatory_field_is_missing() -> None:
    rows = _registry_rows()
    del rows[0]["trader_problem"]

    report = lint_feature_contract_rows(rows)

    assert report.ok is False
    assert any("trader_problem" in error for error in report.errors)
    assert report.can_unlock_confirmed is False


def test_registry_lint_fails_for_duplicate_feature_id() -> None:
    rows = _registry_rows()
    rows[1]["feature_id"] = rows[0]["feature_id"]

    report = lint_feature_contract_rows(rows)

    assert report.ok is False
    assert any("duplicate feature IDs" in error for error in report.errors)


def test_registry_lint_verifies_active_implementation_owners_and_runtime() -> None:
    report = lint_feature_registry()

    assert report.ok is True
    assert report.validated_feature_count == 40
    assert report.runtime_engine.ok is True
    assert report.research_only is True
    assert report.can_unlock_confirmed is False


def test_indicator_runtime_matches_the_pinned_dependencies() -> None:
    runtime = verify_indicator_runtime()

    assert runtime.ok is True
    assert runtime.engine_id == INDICATOR_ENGINE_ID
    assert runtime.engine_version == INDICATOR_ENGINE_VERSION
    assert runtime.expected_packages == runtime.observed_packages


@pytest.mark.parametrize(
    "bindings",
    [
        (
            IndicatorBinding(
                featureId="FTR-012",
                featureVersion="1.0.0",
                minimumWarmupBars=14,
                observationCount=14,
            ),
        ),
        (
            IndicatorBinding(
                featureId="FTR-012",
                featureVersion="1.0.0",
                engineId=INDICATOR_ENGINE_ID,
                engineVersion=INDICATOR_ENGINE_VERSION,
                minimumWarmupBars=14,
                observationCount=14,
            ),
            IndicatorBinding(
                featureId="FTR-013",
                featureVersion="1.0.0",
                engineId="other.engine",
                engineVersion="9.9.9",
                minimumWarmupBars=200,
                observationCount=200,
            ),
        ),
    ],
)
def test_missing_or_mixed_indicator_engines_fail_closed(
    bindings: tuple[IndicatorBinding, ...],
) -> None:
    result = assess_indicator_manifest(bindings)

    assert result.ok is False
    assert result.state is IndicatorInputState.ENGINE_MISMATCH
    assert result.can_emit_indicator_claims is False


def test_insufficient_indicator_warmup_is_input_incomplete() -> None:
    result = assess_indicator_manifest(
        (
            IndicatorBinding(
                featureId="FTR-013",
                featureVersion="1.0.0",
                engineId=INDICATOR_ENGINE_ID,
                engineVersion=INDICATOR_ENGINE_VERSION,
                minimumWarmupBars=200,
                observationCount=199,
            ),
        )
    )

    assert result.ok is False
    assert result.state is IndicatorInputState.INPUT_INCOMPLETE
    assert result.can_emit_indicator_claims is False
    assert "requires 200 bars" in result.errors[0]


def test_indicator_parity_divergence_is_recorded() -> None:
    result = compare_indicator_parity(
        {"rsi14": 50.0, "ema20": 101.0},
        {"rsi14": 50.2, "ema20": 101.0},
    )

    assert result.ok is False
    assert result.state == "PARITY_DIVERGENCE"
    assert result.divergent_keys == ("rsi14",)
    assert result.max_absolute_error == pytest.approx(0.2)


def test_indicator_parity_within_tolerance_is_explicit() -> None:
    result = compare_indicator_parity(
        {"ema20": 100.000000001},
        {"ema20": 100.0},
    )

    assert result.ok is True
    assert result.state == "PARITY_OK"
    assert result.divergent_keys == ()


def test_selection_scan_run_rejects_unpinned_engine_or_registry() -> None:
    with pytest.raises(ValidationError, match="feature registry"):
        SelectionScanRun.create(
            profile_id="PRF-TEST",
            profile_version="1.0.0",
            as_of=AS_OF,
            universe_version="u1",
            data_mode=DataMode.SYNTHETIC_TEST,
            eligible_count=1,
            scanned_count=1,
            feature_registry_version="stale",
        )

    with pytest.raises(ValidationError, match="indicator engine"):
        SelectionScanRun.create(
            profile_id="PRF-TEST",
            profile_version="1.0.0",
            as_of=AS_OF,
            universe_version="u1",
            data_mode=DataMode.SYNTHETIC_TEST,
            eligible_count=1,
            scanned_count=1,
            indicator_engine_id="other.engine",
        )


def test_point_in_time_features_fail_closed_before_warmup() -> None:
    result = build_point_in_time_features(_ohlcv_candles(19))

    assert result["state"] == "INPUT_INCOMPLETE"
    assert result["featureRegistryVersion"] == "1.1.0"
    assert result["indicatorEngineId"] == INDICATOR_ENGINE_ID
    assert "20 closed bars" in result["nullReason"]
    assert "rvol20" not in result


def test_institutional_features_fail_closed_before_full_vector_warmup() -> None:
    result = build_institutional_features(
        _institutional_candles(INSTITUTIONAL_MINIMUM_WARMUP_BARS - 1)
    )

    assert result.state == "INPUT_INCOMPLETE"
    assert result.observation_count == INSTITUTIONAL_MINIMUM_WARMUP_BARS - 1
    assert result.missing == list(INSTITUTIONAL_FEATURE_KEYS)
    assert all(value is None for value in result.values.values())
    assert "requires 200 closed bars" in (result.null_reason or "")


def test_feature_registry_read_only_api_exposes_manifest_and_lint() -> None:
    client = TestClient(app)

    manifest_response = client.get("/api/v1/selection/feature-registry")
    lint_response = client.get("/api/v1/selection/feature-registry/lint")

    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert len(manifest["features"]) == 40
    assert manifest["researchOnly"] is True
    assert manifest["canUnlockConfirmed"] is False
    assert manifest["indicatorEngine"]["engineId"] == INDICATOR_ENGINE_ID

    assert lint_response.status_code == 200
    lint = lint_response.json()
    assert lint["ok"] is True
    assert len(lint["requiredFields"]) == 22
    assert lint["validatedFeatureCount"] == 40
    assert lint["runtimeEngine"]["ok"] is True
    assert lint["canUnlockConfirmed"] is False


def test_unregistered_evidence_claim_is_rejected() -> None:
    with pytest.raises(ValidationError, match="not registered"):
        EvidenceClaim.create(
            feature_id="FTR-999",
            feature_version="1.0.0",
            family=EvidenceFamily.STRUCTURE,
            correlation_group="CG_PRICE_STRUCTURE",
            direction=EvidenceDirection.BULLISH,
            strength_before_caps=0.5,
            source_fact_ids=("fact-1",),
            authority=SourceRole.OFFICIAL_GATE,
            available_at=AS_OF,
            state_ceiling=StateCeiling.CONFIRMED,
            can_support_confirmed=True,
            explanation="Adversarial unregistered feature.",
        )


def test_manifest_rejects_unknown_feature_and_caller_controlled_warmup() -> None:
    unknown = assess_indicator_manifest(
        (
            IndicatorBinding(
                featureId="FTR-999",
                featureVersion="9.9.9",
                engineId=INDICATOR_ENGINE_ID,
                engineVersion=INDICATOR_ENGINE_VERSION,
                minimumWarmupBars=0,
                observationCount=0,
            ),
        )
    )
    bypass = assess_indicator_manifest(
        (
            IndicatorBinding(
                featureId="FTR-013",
                featureVersion="1.0.0",
                engineId=INDICATOR_ENGINE_ID,
                engineVersion=INDICATOR_ENGINE_VERSION,
                minimumWarmupBars=0,
                observationCount=0,
            ),
        )
    )

    assert unknown.ok is False
    assert unknown.state is IndicatorInputState.REGISTRY_MISMATCH
    assert any("not registered" in error for error in unknown.errors)
    assert bypass.ok is False
    assert bypass.state is IndicatorInputState.REGISTRY_MISMATCH
    assert any("match registry 200" in error for error in bypass.errors)
    assert any("requires 200 bars" in error for error in bypass.errors)


def test_indicator_parity_rejects_empty_and_non_finite_inputs() -> None:
    empty = compare_indicator_parity({}, {})
    non_finite = compare_indicator_parity(
        {"rsi14": float("inf")}, {"rsi14": float("inf")}
    )

    assert empty.ok is False
    assert empty.state == "PARITY_INVALID"
    assert empty.compared_count == 0
    assert non_finite.ok is False
    assert non_finite.state == "PARITY_DIVERGENCE"
    assert non_finite.divergent_keys == ("rsi14",)


@pytest.mark.parametrize(
    "mutation", ["duplicate", "partial", "unordered", "mixed_symbol"]
)
def test_point_in_time_features_require_coherent_closed_unique_bars(
    mutation: str,
) -> None:
    candles = _ohlcv_candles(20)
    if mutation == "duplicate":
        candles[-1] = candles[-2].model_copy()
    elif mutation == "partial":
        candles[-1] = candles[-1].model_copy(update={"bar_state": "PARTIAL_PERIOD"})
    elif mutation == "unordered":
        candles[-1], candles[-2] = candles[-2], candles[-1]
    else:
        candles[-1] = candles[-1].model_copy(update={"symbol": "OTHER"})

    result = build_point_in_time_features(candles)

    assert result["state"] == "INPUT_INCOMPLETE"
    assert "nullReason" in result
    assert "rvol20" not in result


def test_feature_calculations_enforce_runtime_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mismatch = RuntimeEngineCheck(
        ok=False,
        engineId=INDICATOR_ENGINE_ID,
        engineVersion=INDICATOR_ENGINE_VERSION,
        expectedPackages={"numpy": "2.4.3", "pandas": "2.3.3"},
        observedPackages={"numpy": "0.0.0", "pandas": "2.3.3"},
        errors=("numpy expected 2.4.3, observed 0.0.0",),
    )
    monkeypatch.setattr(
        feature_engineering_module,
        "verify_indicator_runtime",
        lambda: mismatch,
    )
    monkeypatch.setattr(
        institutional_features_module,
        "verify_indicator_runtime",
        lambda: mismatch,
    )

    point_in_time = build_point_in_time_features(_ohlcv_candles(20))
    institutional = build_institutional_features(
        _institutional_candles(INSTITUTIONAL_MINIMUM_WARMUP_BARS)
    )

    assert point_in_time["state"] == "ENGINE_MISMATCH"
    assert institutional.state == "ENGINE_MISMATCH"
    assert all(value is None for value in institutional.values.values())


def test_institutional_features_reject_partial_bars_and_incomplete_vector() -> None:
    partial = _institutional_candles(INSTITUTIONAL_MINIMUM_WARMUP_BARS)
    partial[-1]["barState"] = "PARTIAL_PERIOD"
    partial_result = build_institutional_features(partial)

    monotonic = _institutional_candles(INSTITUTIONAL_MINIMUM_WARMUP_BARS)
    incomplete_result = build_institutional_features(monotonic)

    assert partial_result.state == "INPUT_INCOMPLETE"
    assert "UNCLOSED" in (partial_result.null_reason or "")
    assert incomplete_result.state == "INPUT_INCOMPLETE"
    assert incomplete_result.missing
    assert "NON_FINITE_OUTPUT" in (incomplete_result.null_reason or "")


def test_registry_lint_rejects_false_research_active_route() -> None:
    rows = _registry_rows()
    target = next(row for row in rows if row["feature_id"] == "FTR-002")
    target["activation_state"] = "RESEARCH_ACTIVE"

    report = lint_feature_contract_rows(rows)

    assert report.ok is False
    assert any("/api/market-context/evaluate" in error for error in report.errors)


def test_scan_run_reconciles_counts_and_rejects_forged_identity() -> None:
    with pytest.raises(ValidationError, match="reconcile exactly"):
        SelectionScanRun.create(
            profile_id="PRF-TEST",
            profile_version="1.0.0",
            as_of=AS_OF,
            universe_version="u1",
            data_mode=DataMode.SYNTHETIC_TEST,
            eligible_count=10,
            scanned_count=9,
            excluded_count=99,
            failed_count=99,
            unattempted_count=99,
        )

    with pytest.raises(ValidationError, match="run_id"):
        SelectionScanRun(
            runId="forged",
            profileId="PRF-TEST",
            profileVersion="1.0.0",
            asOf=AS_OF,
            universeVersion="u1",
            dataMode=DataMode.SYNTHETIC_TEST,
            eligibleCount=1,
            scannedCount=1,
            excludedCount=0,
            failedCount=0,
            unattemptedCount=0,
        )


def test_scan_run_rejects_mixed_indicator_bindings() -> None:
    with pytest.raises(ValidationError, match="indicator manifest"):
        SelectionScanRun.create(
            profile_id="PRF-TEST",
            profile_version="1.0.0",
            as_of=AS_OF,
            universe_version="u1",
            data_mode=DataMode.SYNTHETIC_TEST,
            eligible_count=1,
            scanned_count=1,
            indicator_bindings=(
                IndicatorBinding(
                    featureId="FTR-012",
                    featureVersion="1.0.0",
                    engineId=INDICATOR_ENGINE_ID,
                    engineVersion=INDICATOR_ENGINE_VERSION,
                    minimumWarmupBars=200,
                    observationCount=200,
                ),
                IndicatorBinding(
                    featureId="FTR-013",
                    featureVersion="1.0.0",
                    engineId="other.engine",
                    engineVersion="9.9.9",
                    minimumWarmupBars=200,
                    observationCount=200,
                ),
            ),
        )
