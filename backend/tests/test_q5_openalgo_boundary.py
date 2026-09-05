from __future__ import annotations

import inspect

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api import source_adapters
from trendforge_api.main import app
from trendforge_api.ohlcv_adapter import DataSourceUnavailable
from trendforge_api.openalgo_client import (
    OPENALGO_READ_ONLY_ROUTES,
    OpenAlgoCapabilityReport,
    OpenAlgoCapabilityState,
    OpenAlgoConfig,
    OpenAlgoDataClient,
    OpenAlgoUnavailable,
    assess_openalgo_capability,
)


OPENALGO_ENV_KEYS = (
    "OPENALGO_ENABLED",
    "OPENALGO_BASE_URL",
    "OPENALGO_API_KEY",
    "OPENALGO_ALLOW_REMOTE",
)


def _clear_openalgo_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in OPENALGO_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_absent_configuration_boots_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_openalgo_env(monkeypatch)

    report = assess_openalgo_capability()

    assert report.state == OpenAlgoCapabilityState.ABSENT
    assert report.enabled is False
    assert report.configured is False
    assert report.intraday_confirmation_allowed is False
    assert report.account_access_allowed is False
    assert report.executable is False
    assert report.production_authorized is False
    assert report.blocker_codes == ["OPENALGO_CONFIGURATION_ABSENT"]


def test_configured_boundary_remains_disabled_without_explicit_opt_in() -> None:
    report = assess_openalgo_capability(
        environment={
            "OPENALGO_BASE_URL": "http://127.0.0.1:5000",
            "OPENALGO_API_KEY": "secret-value",
        }
    )

    assert report.state == OpenAlgoCapabilityState.DISABLED
    assert report.configured is True
    assert report.enabled is False
    assert report.blocker_codes == ["OPENALGO_DISABLED_BY_DEFAULT"]


def test_from_env_rejects_credentials_when_boundary_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_openalgo_env(monkeypatch)
    monkeypatch.setenv("OPENALGO_BASE_URL", "http://127.0.0.1:5000")
    monkeypatch.setenv("OPENALGO_API_KEY", "secret-value")

    with pytest.raises(OpenAlgoUnavailable, match="disabled by default"):
        OpenAlgoConfig.from_env()


def test_enabled_local_boundary_stops_at_fixture_verified() -> None:
    report = assess_openalgo_capability(
        environment={
            "OPENALGO_ENABLED": "1",
            "OPENALGO_BASE_URL": "http://127.0.0.1:5000",
            "OPENALGO_API_KEY": "secret-value",
        }
    )

    assert report.state == OpenAlgoCapabilityState.FIXTURE_VERIFIED
    assert report.advertised_read_only_routes == list(OPENALGO_READ_ONLY_ROUTES)
    assert report.blocker_codes == [
        "LIVE_SHADOW_NOT_VERIFIED",
        "REPLAY_INTEGRITY_NOT_VERIFIED",
    ]
    assert report.intraday_confirmation_allowed is False


def test_remote_boundary_is_rejected_without_separate_remote_opt_in() -> None:
    report = assess_openalgo_capability(
        environment={
            "OPENALGO_ENABLED": "1",
            "OPENALGO_BASE_URL": "https://broker.example",
            "OPENALGO_API_KEY": "secret-value",
        }
    )

    assert report.state == OpenAlgoCapabilityState.REJECTED
    assert report.blocker_codes == ["OPENALGO_UNSAFE_BASE_URL"]


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/placeorder",
        "/api/v1/modifyorder",
        "/api/v1/cancelorder",
        "/api/v1/funds",
        "/api/v1/holdings",
        "/api/v1/positions",
    ],
)
def test_execution_or_account_route_forces_rejected_state(route: str) -> None:
    report = assess_openalgo_capability(
        environment={
            "OPENALGO_ENABLED": "1",
            "OPENALGO_BASE_URL": "http://127.0.0.1:5000",
            "OPENALGO_API_KEY": "secret-value",
        },
        advertised_routes=(*OPENALGO_READ_ONLY_ROUTES, route),
    )

    assert report.state == OpenAlgoCapabilityState.REJECTED
    assert report.forbidden_routes_present == [route]
    assert report.blocker_codes == ["FORBIDDEN_EXECUTION_OR_ACCOUNT_ROUTE"]


def test_shadow_live_is_observational_and_does_not_unlock_intraday_confirmation() -> (
    None
):
    report = assess_openalgo_capability(
        environment={
            "OPENALGO_ENABLED": "true",
            "OPENALGO_BASE_URL": "http://localhost:5000",
            "OPENALGO_API_KEY": "secret-value",
        },
        live_shadow_verified=True,
        replay_integrity_passed=True,
    )

    assert report.state == OpenAlgoCapabilityState.SHADOW_LIVE
    assert report.blocker_codes == ["INTRADAY_CONFIRMATION_NOT_PROMOTED"]
    assert report.intraday_confirmation_allowed is False
    assert report.executable is False


def test_shadow_live_model_cannot_be_forged_without_required_proof() -> None:
    with pytest.raises(ValidationError, match="SHADOW_LIVE requires"):
        OpenAlgoCapabilityReport(
            state=OpenAlgoCapabilityState.SHADOW_LIVE,
            enabled=True,
            configured=True,
            fixture_verified=True,
            live_shadow_verified=False,
            replay_integrity_passed=True,
        )


def test_capability_report_never_serializes_api_key() -> None:
    secret = "do-not-leak-this-key"
    report = assess_openalgo_capability(
        environment={
            "OPENALGO_ENABLED": "1",
            "OPENALGO_BASE_URL": "http://127.0.0.1:5000",
            "OPENALGO_API_KEY": secret,
        }
    )

    serialized = report.model_dump_json(by_alias=True)

    assert secret not in serialized
    assert "apiKey" not in serialized
    assert report.config_fingerprint is not None


def test_public_client_surface_contains_no_execution_or_account_method() -> None:
    public_methods = {
        name.lower().replace("_", "")
        for name, member in inspect.getmembers(OpenAlgoDataClient, inspect.isfunction)
        if not name.startswith("_")
    }
    forbidden_terms = {
        "placeorder",
        "modifyorder",
        "cancelorder",
        "orderbook",
        "tradebook",
        "positions",
        "holdings",
        "funds",
        "margin",
        "account",
    }

    assert public_methods.isdisjoint(forbidden_terms)


def test_application_exposes_only_read_only_openalgo_boundary() -> None:
    routes = {
        (getattr(route, "path", ""), frozenset(getattr(route, "methods", set())))
        for route in app.routes
    }
    openalgo_routes = [
        (path, methods)
        for path, methods in routes
        if path.startswith("/api/v1/integrations/openalgo")
    ]
    assert set(openalgo_routes) == {
        ("/api/v1/integrations/openalgo/capability", frozenset({"GET"})),
        ("/api/v1/integrations/openalgo/contract", frozenset({"GET"})),
        ("/api/v1/integrations/openalgo/shadow", frozenset({"GET"})),
    }


def test_capability_endpoint_boots_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_openalgo_env(monkeypatch)

    response = TestClient(app).get("/api/v1/integrations/openalgo/capability")

    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == "Q5-R7"
    assert payload["acceptanceCeiling"] == "NO_INTRADAY_CONFIRMED"
    assert payload["state"] == "ABSENT"
    assert payload["intradayConfirmationAllowed"] is False
    assert payload["accountAccessAllowed"] is False
    assert payload["executable"] is False
    assert payload["productionAuthorized"] is False


def test_source_adapter_rejects_credentials_without_explicit_enable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_openalgo_env(monkeypatch)
    monkeypatch.setenv("OPENALGO_BASE_URL", "http://127.0.0.1:5000")
    monkeypatch.setenv("OPENALGO_API_KEY", "secret-value")

    with pytest.raises(DataSourceUnavailable, match="disabled by default"):
        source_adapters.fetch_openalgo_ohlcv("NSE:RELIANCE", "1m", "5d")
