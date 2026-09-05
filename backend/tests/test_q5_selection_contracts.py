from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api.main import app
from trendforge_api.selection.contracts import (
    DataMode,
    EvidenceDirection,
    EvidenceFamily,
    EventIdentity,
    GateOutcome,
    InstrumentIdentity,
    SelectionCandidate,
    SelectionGateResult,
    SelectionScanRun,
    SelectionState,
    StateCeiling,
    stable_id,
)
from trendforge_api.selection.fixtures import build_q5_r1_fixture_batch
from trendforge_api.source_contracts import (
    SourceContract,
    SourceResult,
    SourceResultState,
    SourceRole,
    source_result_from_endpoint,
)


UTC = timezone.utc
AS_OF = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)
HASH = "a" * 64


def _contract(*, allows_empty: bool = False) -> SourceContract:
    return SourceContract(
        sourceId="SRC-TEST",
        version="1.0.0",
        role=SourceRole.OFFICIAL_GATE,
        schemaVersion="schema-1",
        parserVersion="parser-1",
        allowsValidEmpty=allows_empty,
        emptySemantics=(
            "No rows means no active restriction." if allows_empty else None
        ),
        maxAgeSeconds=86400,
    )


def _endpoint(state: str, **values: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "state": state,
        "fetched_at": AS_OF,
        "record_count": 0,
        "content_hash": HASH,
        "raw_path": "raw/test.json",
        "error_type": None,
        "reason": None,
        "status_code": 200,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_valid_empty_is_distinct_from_blocked_failure() -> None:
    valid_empty = source_result_from_endpoint(
        contract=_contract(allows_empty=True),
        endpoint_result=_endpoint("NO_DATA_NOW"),
        data_date=date(2026, 7, 19),
        published_at=AS_OF - timedelta(hours=2),
        available_at=AS_OF - timedelta(hours=1),
        schema_validated=True,
        parser_validated=True,
        revision_id="r1",
        freshness="FRESH",
    )
    blocked = source_result_from_endpoint(
        contract=_contract(allows_empty=True),
        endpoint_result=_endpoint(
            "BROKEN",
            content_hash=None,
            status_code=403,
            error_type="BLOCK_PAGE",
            reason="Access denied",
        ),
        data_date=None,
        published_at=None,
        available_at=AS_OF,
        schema_validated=False,
        parser_validated=False,
        revision_id="r1",
    )

    assert valid_empty.state is SourceResultState.VALID_EMPTY
    assert valid_empty.ok is True
    assert valid_empty.record_count == 0
    assert valid_empty.empty_semantics
    assert valid_empty.freshness == "FRESH"
    assert valid_empty.can_support_confirmed is False
    assert valid_empty.state_ceiling == "WAIT"
    assert blocked.state is SourceResultState.BLOCKED
    assert blocked.ok is False
    assert blocked.error_type == "BLOCK_PAGE"
    assert blocked.can_support_confirmed is False


def test_structured_result_requires_explicit_freshness_for_confirmation() -> None:
    unknown = source_result_from_endpoint(
        contract=_contract(),
        endpoint_result=_endpoint("RAW_ARCHIVED", record_count=12),
        data_date=date(2026, 7, 19),
        published_at=AS_OF - timedelta(hours=2),
        available_at=AS_OF - timedelta(hours=1),
        schema_validated=True,
        parser_validated=True,
        revision_id="r1",
    )
    fresh = source_result_from_endpoint(
        contract=_contract(),
        endpoint_result=_endpoint("RAW_ARCHIVED", record_count=12),
        data_date=date(2026, 7, 19),
        published_at=AS_OF - timedelta(hours=2),
        available_at=AS_OF - timedelta(hours=1),
        schema_validated=True,
        parser_validated=True,
        revision_id="r1",
        freshness="FRESH",
    )

    assert unknown.state is SourceResultState.STRUCTURED_OK
    assert unknown.freshness == "UNKNOWN"
    assert unknown.can_support_confirmed is False
    assert unknown.state_ceiling == "WAIT"
    assert fresh.state is SourceResultState.STRUCTURED_OK
    assert fresh.freshness == "FRESH"
    assert fresh.can_support_confirmed is True
    assert fresh.state_ceiling == "CONFIRMED"


def test_stale_success_is_fail_closed() -> None:
    result = source_result_from_endpoint(
        contract=_contract(),
        endpoint_result=_endpoint("RAW_ARCHIVED", record_count=12),
        data_date=date(2026, 7, 17),
        published_at=AS_OF - timedelta(days=2),
        available_at=AS_OF - timedelta(days=2),
        schema_validated=True,
        parser_validated=True,
        revision_id="r1",
        freshness="STALE",
    )

    assert result.state is SourceResultState.STALE
    assert result.freshness == "STALE"
    assert result.ok is False
    assert result.can_support_confirmed is False
    assert result.state_ceiling == "WAIT"
    assert result.error_type == "STALE_SOURCE"

def test_raw_archive_without_parser_and_schema_proof_is_partial() -> None:
    result = source_result_from_endpoint(
        contract=_contract(),
        endpoint_result=_endpoint("RAW_ARCHIVED", record_count=12),
        data_date=date(2026, 7, 19),
        published_at=AS_OF - timedelta(hours=2),
        available_at=AS_OF - timedelta(hours=1),
        schema_validated=False,
        parser_validated=False,
        revision_id="r1",
    )

    assert result.state is SourceResultState.PARTIAL
    assert result.ok is False
    assert result.error_type == "RAW_ONLY_NOT_SCANNER_READY"
    assert result.can_support_confirmed is False


def test_unproven_empty_cannot_become_valid_empty() -> None:
    result = source_result_from_endpoint(
        contract=_contract(),
        endpoint_result=_endpoint("NO_DATA_NOW"),
        data_date=date(2026, 7, 19),
        published_at=AS_OF - timedelta(hours=2),
        available_at=AS_OF - timedelta(hours=1),
        schema_validated=True,
        parser_validated=True,
        revision_id="r1",
    )

    assert result.state is SourceResultState.PARTIAL
    assert result.error_type == "UNPROVEN_EMPTY"
    assert result.ok is False


def test_valid_empty_requires_source_date_hash_and_semantics() -> None:
    with pytest.raises(ValidationError, match="empty_semantics"):
        SourceResult(
            sourceId="SRC-TEST",
            contractVersion="1",
            role=SourceRole.OFFICIAL_GATE,
            state=SourceResultState.VALID_EMPTY,
            recordCount=0,
            dataDate=date(2026, 7, 19),
            publishedAt=AS_OF - timedelta(hours=2),
            receivedAt=AS_OF,
            availableAt=AS_OF - timedelta(hours=1),
            retrievedAt=AS_OF,
            schemaVersion="schema-1",
            parserVersion="parser-1",
            revisionId="r1",
            artifactHash=HASH,
            freshness="FRESH",
        )


def test_valid_empty_cannot_be_manually_promoted_to_confirmed() -> None:
    with pytest.raises(
        ValidationError, match="VALID_EMPTY cannot support CONFIRMED"
    ):
        SourceResult(
            sourceId="SRC-TEST",
            contractVersion="1",
            role=SourceRole.OFFICIAL_GATE,
            state=SourceResultState.VALID_EMPTY,
            recordCount=0,
            dataDate=date(2026, 7, 19),
            publishedAt=AS_OF - timedelta(hours=2),
            receivedAt=AS_OF,
            availableAt=AS_OF - timedelta(hours=1),
            retrievedAt=AS_OF,
            schemaVersion="schema-1",
            parserVersion="parser-1",
            revisionId="r1",
            artifactHash=HASH,
            emptySemantics="No active restriction.",
            freshness="FRESH",
            canSupportConfirmed=True,
            stateCeiling="CONFIRMED",
        )

def test_point_in_time_availability_blocks_future_information() -> None:
    result = SourceResult(
        sourceId="SRC-TEST",
        contractVersion="1",
        role=SourceRole.OFFICIAL_GATE,
        state=SourceResultState.STRUCTURED_OK,
        recordCount=1,
        dataDate=date(2026, 7, 19),
        publishedAt=AS_OF - timedelta(hours=1),
        receivedAt=AS_OF + timedelta(seconds=1),
        availableAt=AS_OF,
        retrievedAt=AS_OF + timedelta(seconds=1),
        schemaVersion="schema-1",
        parserVersion="parser-1",
        revisionId="r1",
        artifactHash=HASH,
        freshness="FRESH",
        canSupportConfirmed=True,
        stateCeiling="CONFIRMED",
    )

    assert result.is_available_at(AS_OF - timedelta(microseconds=1)) is False
    assert result.is_available_at(AS_OF) is True
    with pytest.raises(ValueError, match="timezone-aware"):
        result.is_available_at(datetime(2026, 7, 19, 12, 0))


def test_stable_identity_is_order_independent_and_version_sensitive() -> None:
    first = InstrumentIdentity.create(
        exchange="nse",
        segment="equity",
        symbol=" reliance ",
        isin="INE002A01018",
        series="eq",
    )
    second = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQUITY",
        symbol="RELIANCE",
        isin="INE002A01018",
        series="EQ",
    )
    assert first.instrument_id == second.instrument_id
    assert first.symbol == "RELIANCE"

    event_a = EventIdentity.create(
        dataset_root="NSE_BSE_DEALS",
        business_keys={"symbol": "RELIANCE", "date": "2026-07-19"},
    )
    event_b = EventIdentity.create(
        dataset_root="NSE_BSE_DEALS",
        business_keys={"date": "2026-07-19", "symbol": "RELIANCE"},
    )
    assert event_a.event_id == event_b.event_id
    assert stable_id("bar", "x", "adjustment-v1") != stable_id(
        "bar", "x", "adjustment-v2"
    )


def test_required_wait_gate_must_block_confirmed() -> None:
    with pytest.raises(ValidationError, match="must block CONFIRMED"):
        SelectionGateResult(
            code="WAIT_SOURCE",
            outcome=GateOutcome.WAIT,
            blocksConfirmed=False,
            reason="Required source is missing.",
        )


def test_synthetic_candidate_cannot_be_confirmed() -> None:
    instrument = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQUITY",
        symbol="TEST",
        isin="INE000A01010",
        series="EQ",
    )
    run = SelectionScanRun.create(
        profile_id="PRF-TEST",
        profile_version="1",
        as_of=AS_OF,
        universe_version="u1",
        data_mode=DataMode.SYNTHETIC_TEST,
        eligible_count=1,
        scanned_count=1,
    )
    with pytest.raises(ValidationError, match="synthetic/demo"):
        SelectionCandidate(
            candidateId=stable_id("cand", run.run_id, instrument.instrument_id),
            runId=run.run_id,
            instrument=instrument,
            market="NSE",
            profileId=run.profile_id,
            profileVersion=run.profile_version,
            timeframe="1d",
            state=SelectionState.CONFIRMED,
            stateCeiling=StateCeiling.CONFIRMED,
            evidenceDirection=EvidenceDirection.BULLISH,
            discoveryReason="Synthetic test.",
            familySupports=(EvidenceFamily.STRUCTURE,),
            topReason="Synthetic test.",
            nextConfirmation="None.",
            invalidationCondition="Synthetic invalidation.",
            context="Synthetic.",
            freshness="FRESH",
            completeness=1.0,
            whatChanged="Synthetic.",
            evidenceStrength=0.9,
            sourceAgesSeconds={},
            dataMode=DataMode.SYNTHETIC_TEST,
            demoOnly=True,
            executable=False,
        )


def test_q5_r1_fixture_exposes_four_state_schema_but_no_confirmed_output() -> None:
    batch = build_q5_r1_fixture_batch()
    assert set(batch.public_states) == set(SelectionState)
    assert {candidate.state for candidate in batch.candidates} == {
        SelectionState.WATCH,
        SelectionState.WAIT,
        SelectionState.REJECT,
    }
    assert all(
        candidate.state is not SelectionState.CONFIRMED
        for candidate in batch.candidates
    )
    early = next(
        candidate
        for candidate in batch.candidates
        if candidate.instrument.symbol == "TF_WAIT_EARLY_CONFIRM"
    )
    assert early.state is SelectionState.WAIT
    assert "WAIT_Q5_R1_NO_CONFIRMED" in early.gate_codes
    assert early.state_ceiling is StateCeiling.WAIT
    assert all(candidate.executable is False for candidate in batch.candidates)


def test_q5_r1_fixture_api_answers_radar_contract_without_execution_fields() -> None:
    response = TestClient(app).get("/api/v1/selection/fixtures/q5-r1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["milestone"] == "Q5-R1"
    assert payload["acceptanceCeiling"] == "NO_EARLY_CONFIRMED"
    assert set(payload["publicStates"]) == {"WATCH", "WAIT", "CONFIRMED", "REJECT"}
    assert {row["state"] for row in payload["candidates"]} == {
        "WATCH",
        "WAIT",
        "REJECT",
    }

    required_radar_fields = {
        "instrument",
        "profileId",
        "timeframe",
        "state",
        "discoveryReason",
        "familySupports",
        "contradiction",
        "missingProof",
        "nextConfirmation",
        "freshness",
        "completeness",
        "whatChanged",
    }
    forbidden_fields = {
        "trade",
        "entry",
        "stop",
        "target",
        "quantity",
        "orderIntent",
        "winProbability",
    }
    for row in payload["candidates"]:
        assert required_radar_fields <= row.keys()
        assert forbidden_fields.isdisjoint(row.keys())
        assert row["evidenceStrengthLabel"] == (
            "Evidence strength - not win probability"
        )
        assert row["demoOnly"] is True
        assert row["executable"] is False
