from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api.main import app
from trendforge_api.openalgo_client import (
    OPENALGO_FORBIDDEN_ROUTE_TERMS,
    OPENALGO_PROVIDER_COMMIT,
    OPENALGO_PROVIDER_CONTRACT_VERSION,
    OPENALGO_PROVIDER_FILE_HASHES,
    OpenAlgoProviderContractV1,
    OpenAlgoRouteContractV1,
    openalgo_provider_contract,
)


EXPECTED_ROUTES = {
    "/api/v1/ping": "CLIENT_IMPLEMENTED",
    "/api/v1/intervals": "CLIENT_IMPLEMENTED",
    "/api/v1/quotes": "CLIENT_IMPLEMENTED",
    "/api/v1/multiquotes": "CLIENT_IMPLEMENTED",
    "/api/v1/history": "CLIENT_IMPLEMENTED",
    "/api/v1/optionchain": "CLIENT_IMPLEMENTED",
    "/api/v1/optiongreeks": "CLIENT_IMPLEMENTED",
    "/api/v1/multioptiongreeks": "CLIENT_IMPLEMENTED",
}


def test_provider_contract_is_pinned_deterministic_and_secret_free() -> None:
    first = openalgo_provider_contract()
    second = openalgo_provider_contract()

    assert first.schema_version == OPENALGO_PROVIDER_CONTRACT_VERSION
    assert first.provider_commit == OPENALGO_PROVIDER_COMMIT
    assert first.provider_file_hashes == OPENALGO_PROVIDER_FILE_HASHES
    assert len(first.provider_file_hashes) == 11
    assert all(len(digest) == 64 for digest in first.provider_file_hashes.values())
    assert first.contract_hash == second.contract_hash
    assert len(first.contract_hash) == 64
    assert first.secrets_included is False
    assert first.executable is False
    serialized = first.model_dump_json(by_alias=True)
    assert "apiKey" not in serialized
    assert "\"secretsIncluded\":false" in serialized


def test_provider_contract_has_exact_read_only_route_states() -> None:
    contract = openalgo_provider_contract()
    observed = {route.path: route.implementation_state for route in contract.routes}

    assert observed == EXPECTED_ROUTES
    assert all(route.method == "POST" for route in contract.routes)
    assert all("apikey" in route.request_fields for route in contract.routes)
    assert next(route for route in contract.routes if route.path == "/api/v1/ping").response_fields == (
        "status",
        "data",
    )
    assert not any(
        term in route.path.lower()
        for route in contract.routes
        for term in OPENALGO_FORBIDDEN_ROUTE_TERMS
    )


def test_provider_contract_records_unproven_stream_continuity() -> None:
    contract = openalgo_provider_contract()

    assert contract.provider_sequence_available is False
    assert contract.stream_continuity_state == "STREAM_SEQUENCE_UNAVAILABLE"
    assert set(contract.websocket_protocol_variants) == {
        "DOCS:instruments|mode=quote|type=quote",
        "SERVER:symbols|mode=Quote|type=market_data",
    }


def test_provider_contract_rejects_duplicate_or_forbidden_routes() -> None:
    allowed = OpenAlgoRouteContractV1(
        path="/api/v1/quotes",
        method="POST",
        purpose="quote",
        implementation_state="CONTRACT_PINNED",
        request_fields=("apikey", "symbol", "exchange"),
        response_fields=("status", "data"),
    )
    forbidden = allowed.model_copy(update={"path": "/api/v1/placeorder"})

    with pytest.raises(ValidationError, match="routes must be unique"):
        OpenAlgoProviderContractV1(
            contract_hash="0" * 64,
            routes=(allowed, allowed),
        )
    with pytest.raises(ValidationError, match="contains forbidden routes"):
        OpenAlgoProviderContractV1(
            contract_hash="0" * 64,
            routes=(forbidden,),
        )


def test_contract_endpoint_performs_no_configuration_or_broker_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENALGO_API_KEY", raising=False)
    response = TestClient(app).get("/api/v1/integrations/openalgo/contract")

    assert response.status_code == 200
    payload = response.json()
    assert payload["providerCommit"] == OPENALGO_PROVIDER_COMMIT
    assert payload["streamContinuityState"] == "STREAM_SEQUENCE_UNAVAILABLE"
    assert payload["executable"] is False
    assert json.dumps(payload).lower().find("placeorder") == -1
