from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from trendforge_api.market_data_store import ManifestStatus, MarketDataStore
from trendforge_api.openalgo_identity import (
    IdentityState,
    InstrumentIdentityQuery,
    InstrumentKind,
    OpenAlgoInstrumentContract,
    OpenAlgoInstrumentMapper,
)
from trendforge_api.openalgo_replay import OpenAlgoReplayStore
from trendforge_api.openalgo_stream import (
    OpenAlgoStreamManager,
    StreamContinuity,
    StreamRole,
    StreamState,
)


NOW = datetime(2026, 8, 31, 10, 0, tzinfo=UTC)
CONTRACT_HASH = "8cff83dc22937cf69ac6240a30cfcadc6d5cfff2040b01696a9da31651e7a3b9"


def _contracts() -> tuple[OpenAlgoInstrumentContract, ...]:
    return (
        OpenAlgoInstrumentContract(
            exchange="NSE",
            segment="CASH",
            symbol="RELIANCE",
            broker_symbol="RELIANCE-EQ",
            token="2885",
            name="RELIANCE INDUSTRIES",
            instrument_kind=InstrumentKind.EQUITY,
            lot_size=1,
            tick_size=0.05,
            unit="SHARE",
            source_version="master-2026-08-31",
        ),
        OpenAlgoInstrumentContract(
            exchange="NFO",
            segment="DERIVATIVES",
            symbol="RELIANCE24SEP26FUT",
            broker_symbol="RELIANCE-SEP-FUT",
            token="9001",
            name="RELIANCE",
            instrument_kind=InstrumentKind.FUTURE,
            expiry=date(2026, 9, 24),
            lot_size=250,
            tick_size=0.05,
            unit="CONTRACT",
            source_version="master-2026-08-31",
        ),
        OpenAlgoInstrumentContract(
            exchange="NFO",
            segment="DERIVATIVES",
            symbol="RELIANCE24SEP263000CE",
            broker_symbol="RELIANCE-SEP-3000-CE",
            token="9002",
            name="RELIANCE",
            instrument_kind=InstrumentKind.OPTION,
            expiry=date(2026, 9, 24),
            strike=3000,
            option_type="CE",
            lot_size=250,
            tick_size=0.05,
            unit="CONTRACT",
            source_version="master-2026-08-31",
        ),
        OpenAlgoInstrumentContract(
            exchange="MCX",
            segment="COMMODITY_DERIVATIVES",
            symbol="CRUDEOIL17SEP26FUT",
            broker_symbol="CRUDEOIL-SEP-FUT",
            token="7001",
            name="CRUDEOIL",
            instrument_kind=InstrumentKind.FUTURE,
            expiry=date(2026, 9, 17),
            lot_size=100,
            tick_size=1,
            unit="BARREL",
            source_version="master-2026-08-31",
        ),
        OpenAlgoInstrumentContract(
            exchange="MCX",
            segment="COMMODITY_DERIVATIVES",
            symbol="CRUDEOIL16SEP266500CE",
            broker_symbol="CRUDEOIL-SEP-6500-CE",
            token="7002",
            name="CRUDEOIL",
            instrument_kind=InstrumentKind.OPTION,
            expiry=date(2026, 9, 16),
            strike=6500,
            option_type="CE",
            lot_size=100,
            tick_size=0.1,
            unit="BARREL",
            source_version="master-2026-08-31",
        ),
    )


def _mapper(*extra: OpenAlgoInstrumentContract) -> OpenAlgoInstrumentMapper:
    return OpenAlgoInstrumentMapper((*_contracts(), *extra))


def _resolve(
    exchange: str = "NSE", symbol: str = "RELIANCE", as_of: date = date(2026, 8, 31)
):
    return _mapper().resolve(
        InstrumentIdentityQuery(exchange=exchange, symbol=symbol, as_of=as_of)
    )


@pytest.mark.parametrize(
    ("exchange", "symbol", "kind"),
    (
        ("NSE", "RELIANCE", InstrumentKind.EQUITY),
        ("NFO", "RELIANCE24SEP26FUT", InstrumentKind.FUTURE),
        ("NFO", "RELIANCE24SEP263000CE", InstrumentKind.OPTION),
        ("MCX", "CRUDEOIL17SEP26FUT", InstrumentKind.FUTURE),
        ("MCX", "CRUDEOIL16SEP266500CE", InstrumentKind.OPTION),
    ),
)
def test_r17_d_exact_nse_nfo_mcx_identity(exchange, symbol, kind):
    result = _resolve(exchange, symbol)
    assert result.state is IdentityState.EXACT
    assert result.reason_code == "IDENTITY_EXACT"
    assert result.contract is not None
    assert result.contract.instrument_kind is kind


def test_r17_d_unknown_and_cross_segment_fail_closed():
    unknown = _resolve("NSE", "DOESNOTEXIST")
    cross = _resolve("NFO", "RELIANCE")
    assert (unknown.state, unknown.reason_code) == (
        IdentityState.WAIT_IDENTITY,
        "IDENTITY_UNKNOWN",
    )
    assert (cross.state, cross.reason_code) == (
        IdentityState.WAIT_IDENTITY,
        "IDENTITY_CROSS_SEGMENT",
    )


def test_r17_d_expired_contract_fails_closed():
    result = _resolve("NFO", "RELIANCE24SEP26FUT", date(2026, 9, 25))
    assert result.state is IdentityState.WAIT_IDENTITY
    assert result.reason_code == "IDENTITY_EXPIRED"


def test_r17_d_ambiguous_exact_key_fails_closed():
    duplicate = _contracts()[0].model_copy(update={"token": "other-token"})
    mapper = _mapper(duplicate)
    result = mapper.resolve(
        InstrumentIdentityQuery(
            exchange="NSE", symbol="RELIANCE", as_of=date(2026, 8, 31)
        )
    )
    assert result.state is IdentityState.WAIT_IDENTITY
    assert result.reason_code == "IDENTITY_AMBIGUOUS"
    assert result.candidate_count == 2


def test_r17_d_expected_derivative_terms_must_match():
    result = _mapper().resolve(
        InstrumentIdentityQuery(
            exchange="NFO",
            symbol="RELIANCE24SEP263000CE",
            as_of=date(2026, 8, 31),
            expected_expiry=date(2026, 9, 24),
            expected_strike=3100,
            expected_option_type="CE",
        )
    )
    assert result.reason_code == "IDENTITY_CONTRACT_MISMATCH"


def test_r17_d_mapping_hash_is_order_independent():
    first = OpenAlgoInstrumentMapper(_contracts())
    second = OpenAlgoInstrumentMapper(tuple(reversed(_contracts())))
    assert first.mapping_hash == second.mapping_hash


def test_r17_d_openalgo_master_rows_are_strictly_parsed():
    mapper = OpenAlgoInstrumentMapper.from_openalgo_master_rows(
        [
            {
                "exchange": "NFO",
                "symbol": "NIFTY24SEP2625000PE",
                "brsymbol": "NIFTY-SEP-25000-PE",
                "name": "NIFTY",
                "token": "42",
                "expiry": "24-SEP-26",
                "strike": 25000,
                "lotsize": 75,
                "instrumenttype": "OPTIDX",
                "tick_size": 0.05,
            }
        ],
        source_version="provider-master-hash",
    )
    result = mapper.resolve(
        InstrumentIdentityQuery(
            exchange="NFO",
            symbol="NIFTY24SEP2625000PE",
            as_of=date(2026, 8, 31),
        )
    )
    assert result.contract is not None
    assert result.contract.option_type == "PE"
    assert result.contract.strike == 25000


def _normalizer(raw: bytes):
    payload = json.loads(raw)
    data = payload.get("data")
    if not isinstance(data, dict):
        return ()
    return ({"exchange": data["exchange"], "symbol": data["symbol"], "ltp": data["ltp"]},)


def _store(tmp_path) -> MarketDataStore:
    return MarketDataStore(root=tmp_path / "market-data", db_path=tmp_path / "market.db")


def _replay(store: MarketDataStore, normalizer=_normalizer) -> OpenAlgoReplayStore:
    return OpenAlgoReplayStore(
        store,
        normalizer=normalizer,
        parser_version="quote-parser-v1",
        provider_contract_hash=CONTRACT_HASH,
    )


def _raw(ltp: float = 3000.5) -> bytes:
    return json.dumps(
        {"status": "success", "data": {"exchange": "NSE", "symbol": "RELIANCE", "ltp": ltp}}
    ).encode()


def _capture(replay: OpenAlgoReplayStore):
    return replay.capture_populated(
        route="/api/v1/quotes",
        identity=_resolve(),
        raw_content=_raw(),
        request_parameters={"exchange": "NSE", "symbol": "RELIANCE"},
        received_at=NOW,
        trading_date=NOW.date(),
        data_date=NOW.date(),
        freshness_state="CURRENT_FOR_CONTRACT",
        run_id="r17-e-populated",
    )


def test_r17_e_populated_capture_replays_after_restart(tmp_path):
    store = _store(tmp_path)
    capture = _capture(_replay(store))
    restarted = _replay(_store(tmp_path))
    verification = restarted.replay_latest(capture.source_key)
    assert capture.replayable is True
    assert verification.deterministic is True
    assert verification.normalized_row_count == 1
    assert verification.normalized_content_hash == capture.normalized_content_hash
    raw_latest = restarted.store.latest_for(f"{capture.source_key}__raw")
    assert raw_latest is not None
    assert raw_latest.content_hash == capture.raw_content_hash


def test_r17_e_envelope_contains_required_identity_and_lineage(tmp_path):
    replay = _replay(_store(tmp_path))
    capture = _capture(replay)
    latest = replay.store.latest_for(capture.source_key)
    envelope = json.loads(replay.store.object_path_for_hash(latest.content_hash).read_bytes())
    assert envelope["source"] == "OPENALGO"
    assert envelope["qualityState"] == "VALID_POPULATED"
    assert envelope["freshnessState"] == "CURRENT_FOR_CONTRACT"
    assert envelope["providerCommit"]
    assert envelope["providerContractHash"] == CONTRACT_HASH
    assert envelope["rawContentHash"] == capture.raw_content_hash
    assert envelope["payloadHash"] == capture.raw_content_hash
    assert envelope["previousLastGoodHash"] is None
    assert envelope["instrumentIdentity"] == {
        "exchange": "NSE",
        "segment": "CASH",
        "symbol": "RELIANCE",
        "token": "2885",
        "instrumentType": "EQUITY",
        "expiry": None,
        "strike": None,
        "optionType": None,
        "lotSize": 1,
        "tickSize": 0.05,
        "unit": "SHARE",
        "validFrom": None,
        "validTo": None,
        "mappingSource": "OPENALGO_MASTER_CONTRACT",
        "sourceVersion": "master-2026-08-31",
    }


@pytest.mark.parametrize(
    "status", (ManifestStatus.FAILED, ManifestStatus.PARTIAL, ManifestStatus.VALID_EMPTY)
)
def test_r17_e_nonpublishable_never_replaces_last_good(tmp_path, status):
    replay = _replay(_store(tmp_path))
    populated = _capture(replay)
    failed = replay.capture_nonpublishable(
        route="/api/v1/quotes",
        identity=_resolve(),
        status=status,
        reason="fixture is not publishable",
        raw_content=b"{}",
        received_at=NOW + timedelta(seconds=1),
        trading_date=NOW.date(),
        run_id=f"r17-e-{status.value}",
        http_status=200,
    )
    assert failed.attempt.status is status
    assert failed.last_good_hash == populated.last_good_hash
    assert replay.store.latest_for(populated.source_key).content_hash == populated.last_good_hash


def test_r17_e_http_200_empty_object_cannot_publish(tmp_path):
    replay = _replay(_store(tmp_path))
    with pytest.raises(ValueError, match="empty object"):
        replay.capture_populated(
            route="/api/v1/quotes",
            identity=_resolve(),
            raw_content=b"{}",
            request_parameters={"symbol": "RELIANCE", "exchange": "NSE"},
            received_at=NOW,
            trading_date=NOW.date(),
            data_date=NOW.date(),
            freshness_state="CURRENT_FOR_CONTRACT",
            run_id="empty",
        )


def test_r17_e_wait_identity_cannot_publish(tmp_path):
    replay = _replay(_store(tmp_path))
    with pytest.raises(ValueError, match="exact instrument identity"):
        replay.capture_populated(
            route="/api/v1/quotes",
            identity=_resolve("NSE", "MISSING"),
            raw_content=_raw(),
            request_parameters={"symbol": "MISSING", "exchange": "NSE"},
            received_at=NOW,
            trading_date=NOW.date(),
            data_date=NOW.date(),
            freshness_state="CURRENT_FOR_CONTRACT",
            run_id="wait-identity",
        )


@pytest.mark.parametrize("secret_key", ("apikey", "authorization", "access_token"))
def test_r17_e_secrets_cannot_enter_archive(tmp_path, secret_key):
    replay = _replay(_store(tmp_path))
    with pytest.raises(ValueError, match="credential"):
        replay.capture_populated(
            route="/api/v1/quotes",
            identity=_resolve(),
            raw_content=_raw(),
            request_parameters={"symbol": "RELIANCE", secret_key: "do-not-store"},
            received_at=NOW,
            trading_date=NOW.date(),
            data_date=NOW.date(),
            freshness_state="CURRENT_FOR_CONTRACT",
            run_id="secret",
        )


def test_r17_e_corrupted_raw_object_fails_replay(tmp_path):
    replay = _replay(_store(tmp_path))
    capture = _capture(replay)
    raw_path = replay.store.object_path_for_hash(capture.raw_content_hash)
    raw_path.write_bytes(b'{"corrupted":true}')
    with pytest.raises(ValueError, match="content hash mismatch"):
        replay.replay_latest(capture.source_key)


def test_r17_e_different_parser_version_cannot_silently_replay(tmp_path):
    replay = _replay(_store(tmp_path))
    capture = _capture(replay)
    changed = OpenAlgoReplayStore(
        _store(tmp_path),
        normalizer=_normalizer,
        parser_version="quote-parser-v2",
        provider_contract_hash=CONTRACT_HASH,
    )
    with pytest.raises(ValueError, match="parser version"):
        changed.replay_latest(capture.source_key)


def _active_stream(*, max_queue_size=3, protocol="DOCS"):
    manager = OpenAlgoStreamManager(
        enabled=True,
        protocol_variant=protocol,
        max_queue_size=max_queue_size,
        heartbeat_timeout_seconds=10,
    )
    session = manager.begin_connect(at=NOW)
    manager.authentication_result(accepted=True, at=NOW)
    payload = manager.configure_subscriptions(
        evidence_shortlist=(_resolve(),),
        display_only=(_resolve("MCX", "CRUDEOIL17SEP26FUT"),),
    )
    manager.subscription_result(accepted=True, at=NOW)
    return manager, session, payload


def _event(symbol="RELIANCE", exchange="NSE", seconds=1, ltp=3000):
    return {
        "symbol": symbol,
        "exchange": exchange,
        "timestamp": (NOW + timedelta(seconds=seconds)).isoformat(),
        "ltp": ltp,
    }


def test_r17_f_disabled_manager_opens_no_connection():
    manager = OpenAlgoStreamManager(enabled=False)
    assert manager.snapshot().state is StreamState.DISABLED
    with pytest.raises(RuntimeError, match="disabled"):
        manager.begin_connect(at=NOW)


@pytest.mark.parametrize(
    ("protocol", "field", "mode", "kind"),
    (("DOCS", "instruments", "quote", "quote"), ("SERVER", "symbols", "Quote", "market_data")),
)
def test_r17_f_both_pinned_subscription_variants(protocol, field, mode, kind):
    manager, _, payload = _active_stream(protocol=protocol)
    assert payload[field]
    assert payload["mode"] == mode
    assert payload["type"] == kind
    assert manager.snapshot().evidence_subscription_count == 1
    assert manager.snapshot().display_subscription_count == 1


def test_r17_f_one_managed_connection_only():
    manager, _, _ = _active_stream()
    with pytest.raises(RuntimeError, match="one managed"):
        manager.begin_connect(at=NOW)


def test_r17_f_evidence_and_display_events_stay_separate():
    manager, session, _ = _active_stream()
    evidence = manager.ingest(session_id=session, payload=_event(), received_at=NOW)
    display = manager.ingest(
        session_id=session,
        payload=_event("CRUDEOIL17SEP26FUT", "MCX", 2, 6500),
        received_at=NOW,
    )
    assert evidence.role is StreamRole.EVIDENCE_SHORTLIST
    assert display.role is StreamRole.DISPLAY_ONLY
    assert evidence.evidence_eligible is False
    assert display.evidence_eligible is False


def test_r17_f_duplicate_and_reordered_events_fail_closed():
    manager, session, _ = _active_stream()
    assert manager.ingest(session_id=session, payload=_event(seconds=2), received_at=NOW)
    assert manager.ingest(session_id=session, payload=_event(seconds=2), received_at=NOW) is None
    assert manager.ingest(session_id=session, payload=_event(seconds=1), received_at=NOW) is None
    snapshot = manager.snapshot()
    assert snapshot.duplicate_count == 1
    assert snapshot.reordered_count == 1
    assert snapshot.state is StreamState.GAP_DETECTED


def test_r17_f_bounded_queue_marks_gap_without_silent_overwrite():
    manager, session, _ = _active_stream(max_queue_size=1)
    manager.ingest(session_id=session, payload=_event(seconds=1), received_at=NOW)
    assert manager.ingest(session_id=session, payload=_event(seconds=2), received_at=NOW) is None
    snapshot = manager.snapshot()
    assert snapshot.queue_size == 1
    assert snapshot.dropped_count == 1
    assert "WAIT_STREAM_BACKPRESSURE" in snapshot.blocker_codes


def test_r17_f_heartbeat_timeout_marks_gap():
    manager, session, _ = _active_stream()
    assert manager.heartbeat(session_id=session, at=NOW + timedelta(seconds=1))
    assert not manager.check_heartbeat(now=NOW + timedelta(seconds=12))
    assert manager.snapshot().continuity is StreamContinuity.GAP_DETECTED


def test_r17_f_reconnect_requires_new_session_and_resubscription():
    manager, first_session, _ = _active_stream()
    manager.disconnect(reason_code="WAIT_STREAM_DISCONNECTED")
    second_session = manager.begin_connect(at=NOW + timedelta(seconds=2))
    assert second_session != first_session
    assert manager.ingest(
        session_id=first_session, payload=_event(seconds=3), received_at=NOW
    ) is None
    manager.authentication_result(accepted=True, at=NOW + timedelta(seconds=2))
    manager.configure_subscriptions(evidence_shortlist=(_resolve(),))
    manager.subscription_result(accepted=True, at=NOW + timedelta(seconds=2))
    assert manager.snapshot().stale_session_count == 1
    assert manager.snapshot().connection_count == 2


def test_r17_f_rest_fallback_never_repairs_stream_gap():
    manager, _, _ = _active_stream()
    manager.disconnect(reason_code="WAIT_STREAM_DISCONNECTED")
    manager.record_rest_fallback()
    snapshot = manager.snapshot()
    assert snapshot.continuity is StreamContinuity.GAP_DETECTED
    assert snapshot.rest_fallback_repairs_gap is False
    assert "REST_FALLBACK_CANNOT_REPAIR_STREAM_GAP" in snapshot.blocker_codes


def test_r17_f_snapshot_is_secret_free_and_non_executable():
    manager, _, _ = _active_stream()
    serialized = manager.snapshot(now=NOW).model_dump_json()
    assert "apikey" not in serialized.casefold()
    assert manager.snapshot().provider_sequence_available is False
    assert manager.snapshot().secrets_included is False
    assert manager.snapshot().executable is False
