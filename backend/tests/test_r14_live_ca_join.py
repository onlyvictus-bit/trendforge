"""File A R14: official corporate-action join onto the live cash spine (WAIT-only).

These tests freeze the R14 ceiling before the module exists:
- CA is joined through A2/R4 instrument identity, never scrip codes.
- DAT-022 factor semantics (split/bonus/dividend/rights/merger) are copied,
  never re-derived from price alone.
- Replay at decision_at cannot see a CA whose available_at is in the future.
- Unresolved/conflict/identity-break CA means WAIT, never bullish evidence.
- R5 consumes the R14 join DTO as CA authority; confirmedCount stays 0.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.selection import r5_live
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
    CorporateActionVintage,
    ParticipationBaseline,
    _store_raw_bar,
    list_raw_bars,
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
from trendforge_api.selection.r14_live import (
    ACCEPTANCE_CEILING,
    ALGORITHM_VERSION,
    PROFILE_ID,
    SCHEMA_VERSION,
    R14CaJoinBatchV1,
    R14CaJoinRowV1,
    build_r14_ca_join,
    latest_r14_ca_join,
    persist_r14_ca_join,
)
from trendforge_api.selection.r5_live import (
    build_r5_structure_batch,
    persist_r5_structure_batch,
)
from trendforge_api.source_contracts import SourceResult, SourceResultState, SourceRole


TRADING_DATE = date(2026, 8, 14)
DECISION_AT = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)
EFFECTIVE_NEXT_DAY = (TRADING_DATE + timedelta(days=1)).isoformat()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _fixtures(*, symbol: str = "R14TEST", r2_state=SelectionState.WATCH):
    instrument = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQ",
        symbol=symbol if not symbol.isdigit() else "RELIANCE",
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
        candidate_id="candidate-r14",
        symbol=symbol,
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
        cheap_features={},
        source_clock={},
        lineage={"artifactHash": lineage.artifact_hash},
        restriction_state="READY",
        completeness=1.0,
    )
    bundle = InventorySourceBundleV1(
        bundle_id="r1-bundle",
        bundle_hash=_hash("r1"),
        collector_run_id="collector-r14",
        cash_pipeline_run_id="cash-r14",
        cash_pipeline_fingerprint=_hash("pipeline"),
        permission_fingerprint=_hash("permission"),
        snapshot_bundle_id="snapshot-r14",
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
        watch_count=1 if r2_state is SelectionState.WATCH else 0,
        wait_count=1 if r2_state is SelectionState.WAIT else 0,
        reject_count=1 if r2_state is SelectionState.REJECT else 0,
        rows=(
            AttentionRowV1(
                candidate_id=stock.candidate_id,
                symbol=symbol,
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
            ),
        ),
    )
    return instrument, identity, bundle, attention


def _r5_env(identity, bundle):
    history_row = CashHistoryRow(
        symbol=bundle.stock_records[0].symbol,
        instrument_id=bundle.stock_records[0].instrument_id,
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
        artifact_hash=_hash("latest-cash"),
        freshness="FRESH",
        can_support_confirmed=False,
        state_ceiling="WAIT",
    )
    staging = CashStagingBatch(
        result_id=identity.staging_result_id,
        source_result=source_result,
        row_count=1,
        rows=({"symbol": bundle.stock_records[0].symbol},),
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
    return history, staging, context


def _store_flat_history(instrument: InstrumentIdentity, *, days: int = 22) -> None:
    first = TRADING_DATE - timedelta(days=days - 1)
    for index in range(days):
        trade_date = first + timedelta(days=index)
        _store_raw_bar(
            CashRawSessionBar(
                bar_id=f"flat-{index}",
                instrument_id=instrument.instrument_id,
                symbol=instrument.symbol,
                trade_date=trade_date,
                artifact_hash=_hash(f"flat-bar-{trade_date}"),
                series_id="raw-series",
                open=99.5,
                high=100.5,
                low=99.0,
                close=100.0,
                previous_close=100.0,
                volume=1000.0,
                traded_value=100000.0,
            )
        )


def _store_breakout_history(instrument: InstrumentIdentity) -> None:
    first = TRADING_DATE - timedelta(days=21)
    previous = 100.0
    for index in range(22):
        trade_date = first + timedelta(days=index)
        close = 110.0 if index == 21 else 100.0 + index * 0.1
        high = 111.0 if index == 21 else close + 0.5
        _store_raw_bar(
            CashRawSessionBar(
                bar_id=f"bo-{index}",
                instrument_id=instrument.instrument_id,
                symbol=instrument.symbol,
                trade_date=trade_date,
                artifact_hash=_hash(f"bo-bar-{trade_date}"),
                series_id="raw-series",
                open=close - 0.2,
                high=high,
                low=close - 0.5,
                close=close,
                previous_close=previous,
                volume=2500 if index == 21 else 1000,
                traded_value=close * (2500 if index == 21 else 1000),
            )
        )
        previous = close


def _obs(
    *,
    symbol: str = "R14TEST",
    action_class: str = "SPLIT",
    action_type: str | None = None,
    ex_date: str = EFFECTIVE_NEXT_DAY,
    parsed_at: str = "2026-08-01T12:00:00+00:00",
    source: str = "nse_corporate_filings_actions",
    event_id: int = 1,
    numerator: float | None = None,
    denominator: float | None = None,
    cash: float | None = None,
    offer: float | None = None,
    factor: float | None = None,
    revision: str = "ORIGINAL",
    predecessor: str | None = None,
    successor: str | None = None,
    continuity: bool = False,
) -> dict:
    return {
        "id": event_id,
        "source_key": source,
        "symbol": symbol,
        "action_type": action_type or action_class,
        "action_class": action_class,
        "ex_date": ex_date,
        "record_date": ex_date,
        "announcement_date": "2026-07-20",
        "ratio_numerator": numerator,
        "ratio_denominator": denominator,
        "cash_amount": cash,
        "offer_price": offer,
        "adjustment_factor": factor,
        "predecessor_symbol": predecessor,
        "successor_symbol": successor,
        "continuity_confirmed": continuity,
        "revision_status": revision,
        "parsed_at": parsed_at,
    }


def _join(bundle, attention, identity, *, observations=(), vintages=(), decision_at=DECISION_AT, pin=None):
    if pin is None:
        pin = build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    return build_r14_ca_join(
        bundle=bundle,
        attention=attention,
        identity=identity,
        pin=pin,
        observations=list(observations),
        vintages=list(vintages),
        decision_at=decision_at,
    )


def _r5(bundle, attention, identity, join, *, history=None, staging=None, context=None):
    if history is None or staging is None or context is None:
        env_history, env_staging, env_context = _r5_env(identity, bundle)
        history = history or env_history
        staging = staging or env_staging
        context = context or env_context
    return build_r5_structure_batch(
        bundle=bundle,
        attention=attention,
        identity=identity,
        history=history,
        staging=staging,
        context=context,
        ca_join=join,
        decision_at=DECISION_AT,
    )


def test_r14_module_pins_wait_only_ceiling_constants() -> None:
    assert SCHEMA_VERSION == "trendforge.ca-join.v1"
    assert PROFILE_ID == "PRF-R14-CA-JOIN"
    assert ACCEPTANCE_CEILING == "LIVE_CA_JOIN_WAIT_ONLY"
    assert ALGORITHM_VERSION == "DAT-022-v1"


def test_r14_row_validator_forbids_confirmed_vote_and_rank(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-ceiling.db")
    base = dict(
        candidate_id="candidate-r14",
        symbol="R14TEST",
        r2_public_state=SelectionState.WATCH,
        join_status="NONE",
        ca_state="NONE",
        raw_series_id="raw-series",
        identity_continuity="SAME_INSTRUMENT",
        display_order=1,
        why_wait=("R14_LIVE_WAIT_CEILING",),
    )
    with pytest.raises(ValidationError):
        R14CaJoinRowV1(**{**base, "r14_state": SelectionState.CONFIRMED})
    with pytest.raises(ValidationError):
        R14CaJoinRowV1(**{**base, "can_support_confirmed": True})
    with pytest.raises(ValidationError):
        R14CaJoinRowV1(**{**base, "can_affect_rank": True})
    with pytest.raises(ValidationError):
        R14CaJoinRowV1(**{**base, "r14_state": SelectionState.REJECT})
    with pytest.raises(ValidationError):
        R14CaJoinRowV1(**{**base, "why_wait": ()})


def test_r14_batch_validator_forbids_unlock_and_confirmed_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-batch-ceiling.db")
    instrument, identity, bundle, attention = _fixtures()
    batch = _join(bundle, attention, identity)
    payload = batch.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError):
        R14CaJoinBatchV1.model_validate({**payload, "canUnlockConfirmed": True})
    with pytest.raises(ValidationError):
        R14CaJoinBatchV1.model_validate({**payload, "sourceActivationReady": True})
    rows = [dict(row) for row in payload["rows"]]
    rows[0]["r14State"] = "CONFIRMED"
    with pytest.raises(ValidationError):
        R14CaJoinBatchV1.model_validate({**payload, "rows": rows})


def test_r14_no_ca_is_none_state_wait_and_has_no_trade_geometry(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-none.db")
    instrument, identity, bundle, attention = _fixtures()
    batch = _join(bundle, attention, identity)
    row = batch.rows[0]
    assert batch.universe_count == 1
    assert batch.none_count == 1
    assert batch.joined_count == 0
    assert batch.wait_ca_count == 0
    assert batch.can_unlock_confirmed is False
    assert batch.source_activation_ready is False
    assert batch.acceptance_ceiling == "LIVE_CA_JOIN_WAIT_ONLY"
    assert row.join_status == "NONE"
    assert row.ca_state == "NONE"
    assert row.r14_state is SelectionState.WAIT
    assert row.instrument_id == instrument.instrument_id
    assert row.isin == instrument.isin
    assert row.identity_continuity == "SAME_INSTRUMENT"
    assert row.visible_event_ids == ()
    assert row.hidden_future_event_count == 0
    assert row.adjusted_series_id is None
    assert row.factor_version is not None
    assert row.can_support_confirmed is False
    assert row.can_affect_rank is False
    assert row.why_wait
    assert all(
        forbidden not in batch.model_dump_json(by_alias=True)
        for forbidden in ('"entry"', '"target"', '"stop"', '"quantity"', '"winProbability"')
    )


def test_r14_missing_inputs_fail_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-missing.db")
    instrument, identity, bundle, attention = _fixtures()
    from trendforge_api.selection import r14_live

    monkeypatch.setattr(r14_live, "latest_inventory_source_bundle", lambda: None)
    with pytest.raises(ValueError, match="WAIT_R14_R1_R2_NOT_READY"):
        build_r14_ca_join(bundle=None, attention=attention, identity=identity)
    monkeypatch.undo()
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-missing.db")
    mismatched = attention.model_copy(update={"r1_bundle_hash": _hash("other")})
    with pytest.raises(ValueError, match="WAIT_R14_LINEAGE_MISMATCH"):
        build_r14_ca_join(bundle=bundle, attention=mismatched, identity=identity)
    with pytest.raises(ValueError, match="WAIT_R14_R4_NOT_READY"):
        build_r14_ca_join(bundle=bundle, attention=attention, identity=identity)
    pin = build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    newer_r2 = attention.model_copy(update={"run_hash": _hash("r2-new")})
    with pytest.raises(ValueError, match="WAIT_R14_R4_NOT_READY"):
        build_r14_ca_join(
            bundle=bundle, attention=newer_r2, identity=identity, pin=pin
        )


def test_r14_unknown_id_and_companion_scrip_never_join_ca(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-unknown.db")
    _instrument, identity, bundle, attention = _fixtures()
    empty = identity.model_copy(update={"rows": (), "fact_count": 0})
    row = _join(
        bundle, attention, empty, observations=[_obs(numerator=2, denominator=1)]
    ).rows[0]
    assert row.join_status == "UNKNOWN_ID"
    assert row.ca_state == "WAIT_CA"
    assert row.factor_version is None
    assert row.adjusted_series_id is None
    assert row.identity_continuity == "UNPROVEN"
    assert "UNKNOWN_ID" in row.why_wait
    assert row.visible_event_ids == ()

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-companion.db")
    _inst2, identity2, bundle2, attention2 = _fixtures(symbol="500325")
    companion = _join(
        bundle2, attention2, identity2, observations=[_obs(symbol="500325", numerator=2, denominator=1)]
    ).rows[0]
    assert companion.join_status == "COMPANION_REJECTED"
    assert companion.ca_state == "WAIT_CA"
    assert companion.factor_version is None
    assert companion.instrument_id is None


def test_r14_split_two_for_one_factor_orientation_t096(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-split.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_flat_history(instrument)
    batch = _join(
        bundle, attention, identity, observations=[_obs(numerator=2, denominator=1)]
    )
    row = batch.rows[0]
    assert row.join_status == "JOINED"
    assert row.ca_state == "ADJUSTED"
    assert row.joined_events[0].adjustment_factor == pytest.approx(0.5)
    assert row.joined_events[0].affects_volume is True
    assert row.adjusted_series_id is not None
    assert row.visible_event_ids == (row.joined_events[0].action_key,)
    bars, waits = r5_live._closed_bars(
        instrument=instrument,
        raw_bars=list_raw_bars(instrument.symbol, through=TRADING_DATE),
        decision_at=DECISION_AT,
        ca_row=row,
    )
    assert waits == ()
    raw_first = list_raw_bars(instrument.symbol, through=TRADING_DATE)[0]
    assert bars[0].open == pytest.approx(raw_first.open * 0.5)
    assert bars[0].high == pytest.approx(raw_first.high * 0.5)
    assert bars[0].low == pytest.approx(raw_first.low * 0.5)
    assert bars[0].close == pytest.approx(raw_first.close * 0.5)
    assert bars[0].volume == pytest.approx(raw_first.volume / 0.5)


def test_r14_bonus_one_to_one_factor_t096b(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-bonus.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_flat_history(instrument)
    row = _join(
        bundle,
        attention,
        identity,
        observations=[_obs(action_class="BONUS", action_type="BONUS ISSUE", numerator=1, denominator=1)],
    ).rows[0]
    assert row.join_status == "JOINED"
    assert row.joined_events[0].adjustment_factor == pytest.approx(0.5)
    assert row.joined_events[0].affects_volume is True
    bars, waits = r5_live._closed_bars(
        instrument=instrument,
        raw_bars=list_raw_bars(instrument.symbol, through=TRADING_DATE),
        decision_at=DECISION_AT,
        ca_row=row,
    )
    assert waits == ()
    raw_first = list_raw_bars(instrument.symbol, through=TRADING_DATE)[0]
    assert bars[0].close == pytest.approx(raw_first.close * 0.5)
    assert bars[0].volume == pytest.approx(raw_first.volume / 0.5)


def test_r14_dividend_scales_full_ohlc_not_close_only_t097(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-dividend.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_flat_history(instrument)
    row = _join(
        bundle, attention, identity, observations=[_obs(action_class="DIVIDEND", cash=10.0)]
    ).rows[0]
    assert row.join_status == "JOINED"
    assert row.ca_state == "ADJUSTED"
    assert row.joined_events[0].adjustment_factor == pytest.approx(0.9)
    assert row.joined_events[0].affects_volume is False
    bars, waits = r5_live._closed_bars(
        instrument=instrument,
        raw_bars=list_raw_bars(instrument.symbol, through=TRADING_DATE),
        decision_at=DECISION_AT,
        ca_row=row,
    )
    assert waits == ()
    raw_first = list_raw_bars(instrument.symbol, through=TRADING_DATE)[0]
    assert raw_first.open == 99.5
    assert bars[0].open == pytest.approx(99.5 * 0.9)
    assert bars[0].close == pytest.approx(100.0 * 0.9)
    assert bars[0].open != pytest.approx(raw_first.open)
    assert bars[0].volume == pytest.approx(raw_first.volume)


def test_r14_dividend_without_pre_ex_close_waits_t097b(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-dividend-missing.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_flat_history(instrument)
    early_ex = (TRADING_DATE - timedelta(days=60)).isoformat()
    row = _join(
        bundle,
        attention,
        identity,
        observations=[_obs(action_class="DIVIDEND", cash=10.0, ex_date=early_ex)],
    ).rows[0]
    assert row.join_status == "WAIT_DETAILS"
    assert row.ca_state == "WAIT_CA"
    assert row.factor_version is None
    assert row.adjusted_series_id is None
    assert any("PRE_EX" in code for code in row.why_wait)


def test_r14_rights_use_terp_and_missing_offer_waits_t098(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-rights.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_flat_history(instrument)
    row = _join(
        bundle,
        attention,
        identity,
        observations=[
            _obs(action_class="RIGHTS", numerator=1, denominator=4, offer=50.0)
        ],
    ).rows[0]
    assert row.join_status == "JOINED"
    assert row.joined_events[0].adjustment_factor == pytest.approx(0.9)
    assert row.joined_events[0].affects_volume is False
    bars, waits = r5_live._closed_bars(
        instrument=instrument,
        raw_bars=list_raw_bars(instrument.symbol, through=TRADING_DATE),
        decision_at=DECISION_AT,
        ca_row=row,
    )
    raw_first = list_raw_bars(instrument.symbol, through=TRADING_DATE)[0]
    assert bars[0].open == pytest.approx(99.5 * 0.9)
    assert bars[0].volume == pytest.approx(raw_first.volume)

    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-rights-missing.db")
    _store_flat_history(instrument)
    no_offer = _join(
        bundle,
        attention,
        identity,
        observations=[_obs(action_class="RIGHTS", numerator=1, denominator=4)],
    ).rows[0]
    assert no_offer.join_status == "WAIT_DETAILS"
    assert no_offer.ca_state == "WAIT_CA"


def test_r14_merger_ratio_alone_never_adjusts_t099(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-merger.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_flat_history(instrument)
    row = _join(
        bundle,
        attention,
        identity,
        observations=[
            _obs(action_class="MERGER", numerator=3, denominator=2, predecessor="R14TEST", successor="R14TEST", continuity=True)
        ],
    ).rows[0]
    assert row.join_status == "WAIT_DETAILS"
    assert row.ca_state == "WAIT_CA"
    assert row.factor_version is None
    assert row.adjusted_series_id is None
    assert row.joined_events == ()


def test_r14_visible_unresolved_ca_blocks_r5_claims_t013_t178(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-unresolved.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_breakout_history(instrument)
    join = _join(
        bundle,
        attention,
        identity,
        observations=[_obs(action_class="SPLIT", numerator=None, denominator=None)],
    )
    row = join.rows[0]
    assert row.ca_state == "WAIT_CA"
    assert row.join_status == "WAIT_DETAILS"
    batch = _r5(bundle, attention, identity, join)
    r5_row = batch.rows[0]
    assert r5_row.structure_state is SelectionState.WAIT
    assert any(code.startswith("WAIT_CA") for code in r5_row.gate_codes)
    assert r5_row.claim_ids == ()
    assert r5_row.metrics is None
    assert batch.confirmed_count == 0
    assert batch.can_unlock_confirmed is False


def test_r14_future_ca_is_hidden_from_replay(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-future.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_breakout_history(instrument)
    join = _join(
        bundle,
        attention,
        identity,
        observations=[
            _obs(numerator=2, denominator=1, parsed_at="2026-08-21T12:00:00+00:00")
        ],
        vintages=[
            CorporateActionVintage(
                event_id="future-vintage",
                symbol="R14TEST",
                action_class="SPLIT",
                effective_date=TRADING_DATE + timedelta(days=1),
                available_at=DECISION_AT + timedelta(hours=1),
                revision_id="r1",
                adjustment_factor=None,
            )
        ],
    )
    row = join.rows[0]
    assert row.join_status == "NONE"
    assert row.ca_state == "NONE"
    assert row.visible_event_ids == ()
    assert row.hidden_future_event_count >= 1
    batch = _r5(bundle, attention, identity, join)
    r5_row = batch.rows[0]
    assert all(not code.startswith("WAIT_CA") for code in r5_row.gate_codes)
    assert r5_row.claim_ids != ()


def test_r14_conflicting_official_terms_conflict(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-conflict.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_breakout_history(instrument)
    join = _join(
        bundle,
        attention,
        identity,
        observations=[
            _obs(numerator=2, denominator=1),
            _obs(event_id=2, source="bse_corporate_actions", numerator=5, denominator=1),
        ],
    )
    row = join.rows[0]
    assert row.join_status == "CONFLICT"
    assert row.ca_state == "WAIT_CA"
    assert row.factor_version is None
    assert row.joined_events == ()
    r5_row = _r5(bundle, attention, identity, join).rows[0]
    assert "WAIT_CA_CONFLICT" in r5_row.gate_codes
    assert r5_row.claim_ids == ()


def test_r14_cancelled_actions_are_no_action(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-cancelled.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_breakout_history(instrument)
    join = _join(
        bundle,
        attention,
        identity,
        observations=[
            _obs(numerator=2, denominator=1, revision="CANCELLED"),
            _obs(
                event_id=2,
                source="bse_corporate_actions",
                numerator=2,
                denominator=1,
                revision="CANCELLED",
            ),
        ],
    )
    row = join.rows[0]
    assert row.join_status == "CANCELLED"
    assert row.ca_state == "NONE"
    assert row.joined_events == ()
    r5_row = _r5(bundle, attention, identity, join).rows[0]
    assert all(not code.startswith("WAIT_CA") for code in r5_row.gate_codes)


def test_r14_cross_symbol_terms_are_identity_break(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-identity.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_breakout_history(instrument)
    join = _join(
        bundle,
        attention,
        identity,
        observations=[
            _obs(
                action_class="DEMERGER",
                factor=0.72,
                successor="NEWCO",
                continuity=True,
            )
        ],
    )
    row = join.rows[0]
    assert row.join_status == "IDENTITY_BREAK"
    assert row.ca_state == "WAIT_CA"
    assert row.identity_continuity == "BREAK"
    assert row.factor_version is None
    r5_row = _r5(bundle, attention, identity, join).rows[0]
    assert "WAIT_CA_IDENTITY_BREAK" in r5_row.gate_codes
    assert r5_row.claim_ids == ()


def test_r14_new_visible_ca_invalidates_previous_joined_series_t113(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-t113.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_breakout_history(instrument)
    join_one = _join(bundle, attention, identity)
    r5_one = _r5(bundle, attention, identity, join_one)
    assert r5_one.rows[0].claim_ids != ()
    assert r5_one.rows[0].ca_state == "NONE"

    join_two = _join(
        bundle,
        attention,
        identity,
        observations=[_obs(action_class="MERGER", numerator=3, denominator=2)],
    )
    assert join_two.run_hash != join_one.run_hash
    row_two = join_two.rows[0]
    assert row_two.ca_state == "WAIT_CA"
    assert row_two.factor_version is None
    assert row_two.adjusted_series_id is None
    r5_two = _r5(bundle, attention, identity, join_two)
    assert r5_two.run_hash != r5_one.run_hash
    assert r5_two.rows[0].claim_ids == ()
    assert any(code.startswith("WAIT_CA") for code in r5_two.rows[0].gate_codes)
    assert r5_two.confirmed_count == 0


def test_r14_r2_reject_row_stays_reject(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-reject.db")
    instrument, identity, bundle, attention = _fixtures(r2_state=SelectionState.REJECT)
    row = _join(bundle, attention, identity).rows[0]
    assert row.r14_state is SelectionState.REJECT
    assert row.r2_public_state is SelectionState.REJECT


def test_r5_requires_r14_lineage_and_r14_row_per_symbol(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-r5-lineage.db")
    instrument, identity, bundle, attention = _fixtures()
    join = _join(bundle, attention, identity)
    newer_r2 = attention.model_copy(update={"run_hash": _hash("r2-new")})
    with pytest.raises(ValueError, match="WAIT_R5_R14_JOIN_NOT_READY"):
        _r5(bundle, newer_r2, identity, join)
    monkeypatch.setattr(r5_live, "latest_r14_ca_join", lambda: None)
    history, staging, context = _r5_env(identity, bundle)
    with pytest.raises(ValueError, match="WAIT_R5_R14_JOIN_NOT_READY"):
        build_r5_structure_batch(
            bundle=bundle,
            attention=attention,
            identity=identity,
            history=history,
            staging=staging,
            context=context,
            decision_at=DECISION_AT,
        )


def test_r5_consumes_r14_join_and_reports_lineage(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-r5-consume.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_breakout_history(instrument)
    join = _join(
        bundle, attention, identity, observations=[_obs(numerator=2, denominator=1)]
    )
    batch = _r5(bundle, attention, identity, join)
    row = batch.rows[0]
    assert batch.r14_run_id == join.run_id
    assert batch.r14_run_hash == join.run_hash
    assert row.ca_state == "ADJUSTED"
    assert all(not code.startswith("WAIT_CA") for code in row.gate_codes)
    assert "CLOSED_BAR_BREAKOUT" in row.detected_setups
    assert row.claim_ids != ()
    assert row.structure_state is SelectionState.WAIT
    assert batch.confirmed_count == 0


def test_r14_api_is_hash_scoped_read_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r14-api.db")
    instrument, identity, bundle, attention = _fixtures()
    _store_breakout_history(instrument)
    pin = persist_r4_identity_pin(
        build_r4_identity_pin(bundle=bundle, attention=attention, identity=identity)
    )
    stored = persist_r14_ca_join(_join(bundle, attention, identity, pin=pin))
    persist_inventory_source_bundle(bundle)
    persist_attention_order(attention)
    client = TestClient(app)
    response = client.get("/api/v1/selection/ca-join")
    assert response.status_code == 200
    payload = response.json()
    assert payload["runId"] == stored.run_id
    assert payload["schemaVersion"] == SCHEMA_VERSION
    assert payload["canUnlockConfirmed"] is False
    assert payload["acceptanceCeiling"] == ACCEPTANCE_CEILING
    row = payload["rows"][0]
    assert row["joinStatus"] == "NONE"
    assert row["caState"] == "NONE"
    assert row["factorVersion"]
    symbol = client.get("/api/v1/selection/ca-join/R14TEST")
    assert symbol.status_code == 200
    assert symbol.json()["r14State"] == "WAIT"
    missing = client.get("/api/v1/selection/ca-join/NOPE")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "R14_SYMBOL_NOT_FOUND"
    assert client.post("/api/v1/selection/ca-join").status_code == 405

    structure_before = client.get("/api/v1/selection/structure")
    assert structure_before.status_code == 503
    assert structure_before.json()["detail"]["code"] == "R5_STRUCTURE_NOT_READY"

    persist_r5_structure_batch(_r5(bundle, attention, identity, stored))
    structure_response = client.get("/api/v1/selection/structure")
    assert structure_response.status_code == 200
    structure_payload = structure_response.json()
    assert structure_payload["r14RunId"] == stored.run_id
    assert structure_payload["r14RunHash"] == stored.run_hash
    assert structure_payload["confirmedCount"] == 0

    newer_attention = attention.model_copy(
        update={"run_id": "r2-run-newer", "run_hash": _hash("r2-newer")}
    )
    persist_attention_order(newer_attention)
    stale = client.get("/api/v1/selection/ca-join")
    assert stale.status_code == 503
    assert stale.json()["detail"]["code"] == "R14_CA_JOIN_NOT_READY"
    assert latest_r14_ca_join() is not None
