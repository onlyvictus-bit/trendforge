from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.scanners.pk_compatibility import PKUniverseMembershipFixture
from trendforge_api.selection.attention_order import (
    AttentionRowV1,
    InventoryDiscoveryV1,
    persist_attention_order,
)
from trendforge_api.selection.cash_a2_identity import (
    CashIdentityBatch,
    CashIdentityRow,
    RestrictionAssessment,
)
from trendforge_api.selection.contracts import (
    EvidenceDirection,
    InstrumentIdentity,
    NormalizedFact,
    PointInTimeLineage,
    SelectionState,
)
from trendforge_api.selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    StockEvidenceRecordV1,
    persist_inventory_source_bundle,
)
from trendforge_api.selection.r4_live import (
    build_r4_identity_pin,
    persist_r4_identity_pin,
)


TRADING_DATE = date(2026, 8, 14)
DECISION_AT = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _fixtures(*, symbol: str = "R4TEST", instrument_id: str | None = None):
    instrument = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQ",
        symbol=symbol if not symbol.isdigit() else "RELIANCE",
        series="EQ",
        isin="INE000A01001",
    )
    if instrument_id is not None:
        instrument = instrument.model_copy(update={"instrument_id": instrument_id})
    lineage = PointInTimeLineage(
        event_time=DECISION_AT - timedelta(hours=2),
        published_at=DECISION_AT - timedelta(hours=1),
        received_at=DECISION_AT,
        available_at=DECISION_AT - timedelta(minutes=30),
        retrieved_at=DECISION_AT,
        revision_id="r1",
        artifact_hash=_hash("latest-cash"),
    )
    fact = NormalizedFact.create(
        instrument_id=instrument.instrument_id,
        source_id="nse_bhavcopy_eod",
        dataset_root="NSE_CASH_EOD",
        business_keys={"symbol": instrument.symbol, "trade_date": TRADING_DATE.isoformat()},
        data_date=TRADING_DATE,
        lineage=lineage,
        quality_state="STRUCTURED_OK",
        payload={"symbol": instrument.symbol, "close": 110.0},
    )
    identity = CashIdentityBatch(
        batch_id="a2-batch",
        staging_result_id="a1-result",
        calendar_state="OPEN",
        restriction=RestrictionAssessment(
            source_id="nse_fno_ban",
            proven=True,
            can_veto=True,
            state="READY",
            reason="fixture empty ban list",
            data_date=TRADING_DATE.isoformat(),
            artifact_hash=_hash("ban"),
        ),
        fact_count=1,
        rows=(
            CashIdentityRow(
                instrument=instrument,
                fact=fact,
                public_state=SelectionState.WAIT,
                gates=(),
            ),
        ),
    )
    stock = StockEvidenceRecordV1(
        candidate_id="candidate-r4",
        symbol=symbol,
        instrument_id=instrument.instrument_id,
        fact_id=fact.fact_id,
        public_state=SelectionState.WATCH,
        evidence_direction=EvidenceDirection.BULLISH,
        research_class="CASH_RESEARCH",
        why_visible="Current official cash row.",
        why_not_confirmed=("SOURCE_ACTIVATION_FALSE",),
        attempted_sources=("nse_bhavcopy_eod",),
        completed_sources=("nse_bhavcopy_eod",),
        valid_empty_sources=(),
        failed_sources=(),
        not_attempted_sources=(),
        family_coverage={"PARTICIPATION": "AVAILABLE"},
        dataset_root_ids=("NSE_CASH_EOD",),
        supporting_claims=(),
        opposing_claims=(),
        cheap_features={},
        source_clock={},
        lineage={"artifactHash": lineage.artifact_hash},
        restriction_state="READY",
        completeness=1.0,
    )
    bundle = InventorySourceBundleV1(
        bundle_id="r1-bundle",
        bundle_hash=_hash("r1"),
        collector_run_id="collector-r4",
        cash_pipeline_run_id="cash-r4",
        cash_pipeline_fingerprint=_hash("pipeline"),
        permission_fingerprint=_hash("permission"),
        snapshot_bundle_id="snapshot-r4",
        trading_date=TRADING_DATE,
        built_at=DECISION_AT,
        registry_sha256=_hash("registry"),
        source_contract_count=0,
        stock_record_count=1,
        stage_states={"C1": "COMPLETED"},
        source_records=(),
        stock_records=(stock,),
    )
    attention = InventoryDiscoveryV1(
        run_id="r2-run",
        run_hash=_hash("r2"),
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        collector_run_id=bundle.collector_run_id,
        cash_pipeline_run_id=bundle.cash_pipeline_run_id,
        cash_pipeline_fingerprint=bundle.cash_pipeline_fingerprint,
        permission_fingerprint=bundle.permission_fingerprint,
        snapshot_bundle_id=bundle.snapshot_bundle_id,
        trading_date=TRADING_DATE.isoformat(),
        built_at=DECISION_AT,
        universe_count=1,
        watch_count=1,
        wait_count=0,
        reject_count=0,
        rows=(
            AttentionRowV1(
                candidate_id=stock.candidate_id,
                symbol=symbol,
                public_state=SelectionState.WATCH,
                evidence_direction=EvidenceDirection.BULLISH,
                display_order=1,
                attention_rank=1,
                attention_priority=0.9,
                attention_band="HIGH",
                supporting_families=("CASH_SESSION_ROOT",),
                opposing_claims=(),
                missing_evidence=(),
                conflicts=(),
                completeness=1.0,
                freshness="CURRENT",
                source_quality="OFFICIAL_STRUCTURED",
                restriction_state="READY",
                why_visible=stock.why_visible,
                why_not_confirmed=stock.why_not_confirmed,
                lineage=stock.lineage,
                dataset_root_ids=stock.dataset_root_ids,
            ),
        ),
    )
    return instrument, identity, bundle, attention


def test_r4_pins_a2_identity_and_cannot_vote(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r4.db")
    instrument, identity, bundle, attention = _fixtures()
    batch = build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    row = batch.rows[0]
    assert batch.acceptance_ceiling == "LIVE_ID_PIN_WAIT_ONLY"
    assert batch.can_unlock_confirmed is False
    assert batch.pk_upstream_can_vote is False
    assert batch.pk_runtime_required is False
    assert batch.pinned_id_count == 1
    assert batch.unknown_id_count == 0
    assert row.identity_status == "PINNED"
    assert row.instrument_id == instrument.instrument_id
    assert row.r2_public_state is SelectionState.WATCH
    assert row.r4_state is SelectionState.WAIT
    assert row.pk_can_vote is False
    assert row.can_affect_rank is False
    assert "R4_LIVE_WAIT_CEILING" in row.why_wait
    assert "entry" not in batch.model_dump_json(by_alias=True)


def test_r4_unknown_id_is_explicit_not_silent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r4-unknown.db")
    instrument, identity, bundle, attention = _fixtures()
    empty = identity.model_copy(update={"rows": (), "fact_count": 0})
    row = build_r4_identity_pin(
        bundle=bundle, attention=attention, identity=empty
    ).rows[0]
    assert row.identity_status == "UNKNOWN_ID"
    assert row.instrument_id is None
    assert "UNKNOWN_ID" in row.why_wait


def test_r4_rejects_companion_scrip_code(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r4-scrip.db")
    _instrument, identity, bundle, attention = _fixtures(symbol="500325")
    row = build_r4_identity_pin(
        bundle=bundle, attention=attention, identity=identity
    ).rows[0]
    assert row.identity_status == "COMPANION_REJECTED"
    assert row.instrument_id is None
    assert "COMPANION_SCRIP_CODE_NOT_IDENTITY" in row.why_wait


def test_r4_pit_fixture_hides_delisted_name(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r4-pit.db")
    instrument, identity, bundle, attention = _fixtures()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    delisted = datetime(2026, 2, 1, tzinfo=timezone.utc)
    row = build_r4_identity_pin(
        bundle=bundle,
        attention=attention,
        identity=identity,
        membership=(
            PKUniverseMembershipFixture(
                instrument_id=instrument.instrument_id,
                symbol=instrument.symbol,
                member_from=start,
                member_until=delisted,
                delisted_at=delisted,
                available_at=start,
            ),
        ),
        decision_at=DECISION_AT,
    ).rows[0]
    assert row.pit_status == "PIT_DELISTED_OR_OUT"
    assert "PIT_DELISTED_OR_OUT" in row.why_wait


def test_r4_api_is_hash_scoped_and_wait_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r4-api.db")
    _instrument, identity, bundle, attention = _fixtures()
    persist_inventory_source_bundle(bundle)
    persist_attention_order(attention)
    stored = persist_r4_identity_pin(
        build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    )
    client = TestClient(app)
    response = client.get("/api/v1/selection/identity-pin")
    assert response.status_code == 200
    payload = response.json()
    assert payload["runId"] == stored.run_id
    assert payload["canUnlockConfirmed"] is False
    assert payload["pkUpstreamCanVote"] is False
    symbol = client.get("/api/v1/selection/identity-pin/R4TEST")
    assert symbol.status_code == 200
    assert symbol.json()["r4State"] == "WAIT"
    assert symbol.json()["identityStatus"] == "PINNED"
    assert client.post("/api/v1/selection/identity-pin").status_code == 405
