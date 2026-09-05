"""S4 structure pack tests (File A SEL-005, WAIT ceiling)."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta, time
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.selection.attention_order import (
    AttentionRowV1,
    InventoryDiscoveryV1,
    persist_attention_order,
)
from trendforge_api.selection.cash_a1_staging import CashStagingBatch
from trendforge_api.selection.cash_a2_identity import (
    CashIdentityBatch,
    CashIdentityRow,
    RestrictionAssessment,
)
from trendforge_api.selection.cash_a4_history import (
    CashHistoryBatch,
    CashHistoryRow,
    CashRawSessionBar,
    ParticipationBaseline,
    _store_raw_bar,
)
from trendforge_api.selection.contracts import (
    EvidenceDirection,
    InstrumentIdentity,
    NormalizedFact,
    PointInTimeLineage,
    SelectionState,
)
from trendforge_api.selection.index_a5_context import CashContextBatch, IndexContext
from trendforge_api.selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    StockEvidenceRecordV1,
    persist_inventory_source_bundle,
)
from trendforge_api.selection.r4_live import build_r4_identity_pin, persist_r4_identity_pin
from trendforge_api.selection.r14_live import build_r14_ca_join, persist_r14_ca_join
from trendforge_api.selection.r5_live import (
    build_r5_structure_batch,
    persist_r5_structure_batch,
)
from trendforge_api.selection.s4_structure_pack import (
    GROUP_COMPRESSION,
    GROUP_PATTERN_STRUCTURE,
    GROUP_PRICE_STRUCTURE,
    S4StructurePackBatchV1,
    build_s4_structure_pack,
    shortlist_symbols,
)
from trendforge_api.source_contracts import SourceResult, SourceResultState, SourceRole


TRADING_DATE = date(2026, 8, 14)
DECISION_AT = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)
IST = ZoneInfo("Asia/Kolkata")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _ca_join(bundle, attention, identity, *, observations=()):
    pin = build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    return build_r14_ca_join(
        bundle=bundle,
        attention=attention,
        identity=identity,
        pin=pin,
        observations=list(observations),
        vintages=[],
        decision_at=DECISION_AT,
    )


def _fixtures(*, r2_state: SelectionState = SelectionState.WATCH):
    instrument = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQ",
        symbol="R5TEST",
        series="EQ",
        isin="INE000A01001",
    )
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
        business_keys={"symbol": "R5TEST", "trade_date": TRADING_DATE.isoformat()},
        data_date=TRADING_DATE,
        lineage=lineage,
        quality_state="STRUCTURED_OK",
        payload={"symbol": "R5TEST", "close": 110.0},
    )
    identity_row = CashIdentityRow(
        instrument=instrument,
        fact=fact,
        public_state=SelectionState.WAIT,
        gates=(),
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
        rows=(identity_row,),
    )
    history_row = CashHistoryRow(
        symbol="R5TEST",
        instrument_id=instrument.instrument_id,
        raw_series_id="raw-series",
        ca_state="NONE",
        baseline=ParticipationBaseline(
            session_count=20,
            median_volume=1000,
            median_turnover=100000,
            median_range_pct=0.02,
            complete=True,
            reason="fixture",
        ),
        public_note="No visible corporate action.",
    )
    history = CashHistoryBatch(
        batch_id="a4-batch",
        identity_batch_id=identity.batch_id,
        decision_at=DECISION_AT,
        raw_bar_count=22,
        row_count=1,
        rows=(history_row,),
    )
    stock = StockEvidenceRecordV1(
        candidate_id="candidate-r5",
        symbol="R5TEST",
        instrument_id=instrument.instrument_id,
        fact_id=fact.fact_id,
        public_state=r2_state,
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
        cheap_features={
            "returnPercentile": 0.9,
            "volumePercentile": 0.9,
            "turnoverPercentile": 0.9,
        },
        source_clock={
            "nse_bhavcopy_eod": {
                "usabilityState": "USABLE_CURRENT",
                "dataDate": TRADING_DATE.isoformat(),
            }
        },
        lineage={"artifactHash": lineage.artifact_hash},
        restriction_state="READY",
        completeness=1.0,
    )
    bundle = InventorySourceBundleV1(
        bundle_id="r1-bundle",
        bundle_hash=_hash("r1"),
        collector_run_id="collector-r5",
        cash_pipeline_run_id="cash-r5",
        cash_pipeline_fingerprint=_hash("pipeline"),
        permission_fingerprint=_hash("permission"),
        snapshot_bundle_id="snapshot-r5",
        trading_date=TRADING_DATE,
        built_at=DECISION_AT,
        registry_sha256=_hash("registry"),
        source_contract_count=0,
        stock_record_count=1,
        stage_states={"C1": "COMPLETED"},
        source_records=(),
        stock_records=(stock,),
    )
    attention_row = AttentionRowV1(
        candidate_id=stock.candidate_id,
        symbol=stock.symbol,
        public_state=r2_state,
        evidence_direction=stock.evidence_direction,
        display_order=1,
        attention_rank=1 if r2_state is SelectionState.WATCH else None,
        attention_priority=0.9 if r2_state is SelectionState.WATCH else None,
        attention_band="HIGH" if r2_state is SelectionState.WATCH else "UNRANKED",
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
        watch_count=1 if r2_state is SelectionState.WATCH else 0,
        wait_count=1 if r2_state is SelectionState.WAIT else 0,
        reject_count=1 if r2_state is SelectionState.REJECT else 0,
        rows=(attention_row,),
    )
    source_result = SourceResult(
        source_id="nse_bhavcopy_eod",
        contract_version="a1-staging-1",
        role=SourceRole.OFFICIAL_GATE,
        state=SourceResultState.STRUCTURED_OK,
        record_count=1,
        data_date=TRADING_DATE,
        published_at=DECISION_AT - timedelta(hours=1),
        received_at=DECISION_AT,
        available_at=DECISION_AT - timedelta(minutes=30),
        retrieved_at=DECISION_AT,
        schema_version="fixture",
        parser_version="fixture",
        revision_id="r1",
        artifact_hash=lineage.artifact_hash,
        freshness="FRESH",
        can_support_confirmed=False,
        state_ceiling="WAIT",
    )
    staging = CashStagingBatch(
        result_id=identity.staging_result_id,
        source_result=source_result,
        row_count=1,
        rows=({"symbol": "R5TEST"},),
    )
    context = CashContextBatch(
        batch_id="a5-batch",
        index=IndexContext(
            contract_digest=_hash("index-contract"),
            parser_state="PARSED_STRUCTURED",
            data_date=TRADING_DATE.isoformat(),
            artifact_hash=_hash("index"),
            nifty50_close=25000,
            registry_note="fixture official index context",
        ),
        row_count=0,
        rows=(),
    )
    return instrument, identity, history, bundle, attention, staging, context


def _store_breakout_history(instrument: InstrumentIdentity) -> None:
    first = TRADING_DATE - timedelta(days=21)
    previous = 100.0
    for index in range(22):
        trade_date = first + timedelta(days=index)
        close = 110.0 if index == 21 else 100.0 + index * 0.1
        high = 111.0 if index == 21 else close + 0.5
        low = close - 0.5
        artifact = _hash(f"bar-{trade_date}")
        _store_raw_bar(
            CashRawSessionBar(
                bar_id=f"bar-{index}",
                instrument_id=instrument.instrument_id,
                symbol=instrument.symbol,
                trade_date=trade_date,
                artifact_hash=artifact,
                series_id="raw-series",
                open=close - 0.2,
                high=high,
                low=low,
                close=close,
                previous_close=previous,
                volume=2500 if index == 21 else 1000,
                traded_value=close * (2500 if index == 21 else 1000),
            )
        )
        previous = close


def _store_nr_only_history(instrument: InstrumentIdentity) -> None:
    """Flat closes with a shrinking final range: NR7 fires, breakout does not."""
    first = TRADING_DATE - timedelta(days=21)
    previous = 100.0
    for index in range(22):
        trade_date = first + timedelta(days=index)
        close = 100.0
        spread = 0.8 if index < 21 else 0.05
        high = close + spread / 2
        low = close - spread / 2
        artifact = _hash(f"nr-bar-{trade_date}")
        _store_raw_bar(
            CashRawSessionBar(
                bar_id=f"nr-bar-{index}",
                instrument_id=instrument.instrument_id,
                symbol=instrument.symbol,
                trade_date=trade_date,
                artifact_hash=artifact,
                series_id="raw-series",
                open=close,
                high=high,
                low=low,
                close=close,
                previous_close=previous,
                volume=1000,
                traded_value=close * 1000,
            )
        )
        previous = close


def _build_r5(instrument, identity, history, bundle, attention, staging, context, *, decision_at=None):
    return build_r5_structure_batch(
        bundle=bundle,
        attention=attention,
        identity=identity,
        history=history,
        staging=staging,
        context=context,
        ca_join=_ca_join(bundle, attention, identity),
        decision_at=decision_at or DECISION_AT,
    )


def test_s4_breakout_pack_one_price_structure_representative(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4.db")
    instrument, identity, history, bundle, attention, staging, context = _fixtures()
    _store_breakout_history(instrument)
    r5 = _build_r5(instrument, identity, history, bundle, attention, staging, context)
    pack = build_s4_structure_pack(r5=r5)
    assert isinstance(pack, S4StructurePackBatchV1)
    assert pack.confirmed_count == 0
    assert pack.acceptance_ceiling == "LIVE_S4_WAIT_REJECT_ONLY"
    assert pack.can_unlock_confirmed is False
    assert pack.source_activation_ready is False
    row = pack.rows[0]
    tags = {tag.tag for tag in row.setup_tags}
    assert "BREAKOUT_ACCEPTED" in tags
    assert "TREND_ACCEPTANCE_ABOVE_LEVEL" in tags
    price_tags = [
        tag for tag in row.setup_tags if tag.correlation_group == GROUP_PRICE_STRUCTURE
    ]
    reps = {tag.claim_id for tag in price_tags}
    assert len(reps) == 1
    assert reps == {row.price_structure_representative_claim_id}
    # T6: labels non-empty on WAIT rows.
    assert row.next_trigger.startswith("WAIT ")
    assert row.invalidation_condition.strip()
    json_blob = pack.model_dump_json(by_alias=True)
    for forbidden in ('"entry"', '"t1"', '"t2"', '"quantity"', '"winProbability"'):
        assert forbidden not in json_blob


def test_s4_unclosed_bars_produce_no_breakout_claim(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4-unclosed.db")
    instrument, identity, history, bundle, attention, staging, context = _fixtures()
    _store_breakout_history(instrument)
    mid_session = datetime.combine(TRADING_DATE, time(10, 0), tzinfo=IST)
    r5 = _build_r5(
        instrument, identity, history, bundle, attention, staging, context,
        decision_at=mid_session,
    )
    pack = build_s4_structure_pack(r5=r5)
    row = pack.rows[0]
    breakout_tags = [
        tag
        for tag in row.setup_tags
        if tag.correlation_group == GROUP_PRICE_STRUCTURE and tag.feature_id != "FTR-005"
    ]
    assert breakout_tags == []
    assert row.price_structure_representative_claim_id is None
    assert any(code.startswith("WAIT_") for code in row.gate_codes)


def test_s4_wait_ca_rows_carry_no_claims(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4-ca.db")
    instrument, identity, history, bundle, attention, staging, context = _fixtures()
    _store_breakout_history(instrument)
    unresolved_merger = {
        "id": 1,
        "source_key": "nse_corporate_filings_actions",
        "symbol": "R5TEST",
        "action_type": "MERGER",
        "action_class": "MERGER",
        "ex_date": TRADING_DATE.isoformat(),
        "record_date": TRADING_DATE.isoformat(),
        "ratio_numerator": 3,
        "ratio_denominator": 2,
        "revision_status": "ORIGINAL",
        "parsed_at": "2026-08-01T12:00:00+00:00",
    }
    r5 = build_r5_structure_batch(
        bundle=bundle,
        attention=attention,
        identity=identity,
        history=history,
        staging=staging,
        context=context,
        ca_join=_ca_join(bundle, attention, identity, observations=[unresolved_merger]),
        decision_at=DECISION_AT,
    )
    assert r5.rows[0].claim_ids == ()
    pack = build_s4_structure_pack(r5=r5)
    row = pack.rows[0]
    assert all(tag.claim_id is None for tag in row.setup_tags)
    assert row.next_trigger.startswith("UNKNOWN_GAP_WAIT_CA")


def test_s4_nr7_alone_stays_wait(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4-nr.db")
    instrument, identity, history, bundle, attention, staging, context = _fixtures()
    _store_nr_only_history(instrument)
    r5 = _build_r5(instrument, identity, history, bundle, attention, staging, context)
    pack = build_s4_structure_pack(r5=r5)
    row = pack.rows[0]
    assert row.research_state is SelectionState.WAIT
    nr_tags = [
        tag for tag in row.setup_tags if tag.correlation_group == GROUP_COMPRESSION
    ]
    assert len(nr_tags) == 1
    assert nr_tags[0].can_support_confirmed is False
    assert pack.confirmed_count == 0
    # Compression alone qualifies for the bounded S5 shortlist but never confirms.
    assert row.price_structure_representative_claim_id is None
    assert shortlist_symbols(pack) == ("R5TEST",)


def test_s4_pattern_lane_never_supports_confirmed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4-pattern.db")
    instrument, identity, history, bundle, attention, staging, context = _fixtures()
    _store_breakout_history(instrument)
    r5 = _build_r5(instrument, identity, history, bundle, attention, staging, context)
    pack = build_s4_structure_pack(
        r5=r5, pattern_tags_by_symbol={"R5TEST": ("HARMONIC_BAT",)}
    )
    row = pack.rows[0]
    assert row.pattern_lane[0].pattern == "HARMONIC_BAT"
    assert row.pattern_lane[0].can_support_confirmed is False
    pattern_groups = [
        tag
        for tag in row.setup_tags
        if tag.correlation_group == GROUP_PATTERN_STRUCTURE
    ]
    assert pattern_groups == []
    assert "PATTERN_LANE_NOT_EVALUATED_R5_ONLY" not in row.why_unknown
    bare = build_s4_structure_pack(r5=r5)
    assert "PATTERN_LANE_NOT_EVALUATED_R5_ONLY" in bare.rows[0].why_unknown


def test_s4_lineage_and_counts_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4-api.db")
    instrument, identity, history, bundle, attention, staging, context = _fixtures()
    _store_breakout_history(instrument)
    persist_inventory_source_bundle(bundle)
    persist_attention_order(attention)
    pin = persist_r4_identity_pin(
        build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    )
    join = persist_r14_ca_join(
        build_r14_ca_join(
            bundle=bundle,
            attention=attention,
            identity=identity,
            pin=pin,
            observations=[],
            vintages=[],
            decision_at=DECISION_AT,
        )
    )
    stored = persist_r5_structure_batch(
        build_r5_structure_batch(
            bundle=bundle,
            attention=attention,
            identity=identity,
            history=history,
            staging=staging,
            context=context,
            ca_join=join,
            decision_at=DECISION_AT,
        )
    )
    client = TestClient(app)
    response = client.get("/api/v1/selection/s4-structure")
    assert response.status_code == 200
    body = response.json()
    assert body["r14RunId"] == join.run_id
    assert body["r14RunHash"] == stored.r14_run_hash
    assert body["confirmedCount"] == 0
    assert client.post("/api/v1/selection/s4-structure").status_code == 405


def test_s4_get_is_503_without_persisted_r5(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4-empty.db")
    client = TestClient(app)
    response = client.get("/api/v1/selection/s4-structure")
    assert response.status_code == 503


def test_s4_reject_row_keeps_labels_but_no_claims(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "s4-reject.db")
    instrument, identity, history, bundle, attention, staging, context = _fixtures(
        r2_state=SelectionState.REJECT
    )
    _store_breakout_history(instrument)
    r5 = _build_r5(instrument, identity, history, bundle, attention, staging, context)
    pack = build_s4_structure_pack(r5=r5)
    row = pack.rows[0]
    assert row.research_state is SelectionState.REJECT
    assert row.price_structure_representative_claim_id is None
    assert row.next_trigger.strip() and row.invalidation_condition.strip()
