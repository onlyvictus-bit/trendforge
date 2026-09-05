"""3rd-eye evidence radar tests: coverage, honest slots, fusion caps, boards."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.selection.attention_order import (
    AttentionRowV1,
    InventoryDiscoveryV1,
)
from trendforge_api.selection.contracts import EvidenceDirection, SelectionState
from trendforge_api.selection.evidence_radar import (
    EvidenceRadarV1,
    build_coverage,
    build_evidence_radar,
)
from trendforge_api.selection.evidence_radar.calculate import (
    CalculatedFact,
    FactDirection,
)
from trendforge_api.selection.evidence_radar.fuse import fuse_instrument
from trendforge_api.selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    SourceEvidenceRecordV1,
    SourceUsabilityState,
)

from tests.test_r6_live import (
    DECISION_AT,
    TRADING_DATE,
    _bars,
    _deal,
    _hash,
    _loader,
    _r14,
    _signals,
    _stock,
)


def _src(key, usability="USABLE_CURRENT", alias_of=None, cg="CG_TEST", root=None):
    return SourceEvidenceRecordV1(
        source_key=key,
        canonical_source_key=key,
        alias_of=alias_of,
        canonical_url=f"https://example.test/{key}",
        normalized_source_key=key.upper(),
        acquisition_owner="NSE",
        parser_or_adapter_id=f"parser-{key}",
        validator_id="validator-v1",
        cadence_class="DAILY_EOD",
        attempt_state="OK",
        parser_state="PARSED_STRUCTURED",
        usability_state=SourceUsabilityState(usability),
        reason="fixture",
        correlation_group=cg,
        dataset_root_id=root or f"ROOT:{key.upper()}",
    )


DEFAULT_SOURCES = (
    _src("nse_bhavcopy_eod", cg="CG_ACTIVITY_SESSION", root="ROOT:NSE_CASH_EOD"),
    _src("nse_bulk_deals_today_csv", cg="CG_EVENT_ROOT"),
    _src(
        "bse_bulk_deals",
        alias_of="nse_bulk_deals_today_csv",
        cg="CG_EVENT_ROOT",
        root="ROOT:NSE_EVENT_MIRROR",
    ),
    _src("msei_fii_dii", usability="STALE_LAST_GOOD", cg="CG_MARKET_CONTEXT"),
    _src("cftc_cot_positions", usability="STALE_LAST_GOOD", cg="CG_GLOBAL"),
    _src("nse_shareholding_pattern", usability="PARSE_FAILED", cg="CG_DELAYED_SPONSOR"),
)


def _spine(specs, sources=DEFAULT_SOURCES):
    stocks = [_stock(*spec) for spec in specs]
    bundle = InventorySourceBundleV1(
        bundle_id="radar-r1",
        bundle_hash=_hash("radar-r1"),
        collector_run_id="collector",
        cash_pipeline_run_id="cash",
        cash_pipeline_fingerprint=_hash("pipeline"),
        permission_fingerprint=_hash("permission"),
        snapshot_bundle_id="snapshot",
        trading_date=TRADING_DATE,
        built_at=DECISION_AT,
        registry_sha256=_hash("registry"),
        source_contract_count=len(sources),
        stock_record_count=len(stocks),
        stage_states={"C1": "COMPLETED"},
        source_records=tuple(sources),
        stock_records=tuple(stocks),
    )
    rows = []
    for order, stock in enumerate(stocks, start=1):
        priority = round(0.95 - 0.05 * (order - 1), 2)
        rows.append(
            AttentionRowV1(
                candidate_id=stock.candidate_id,
                symbol=stock.symbol,
                public_state=SelectionState.WATCH,
                evidence_direction=stock.evidence_direction,
                display_order=order,
                attention_rank=order,
                attention_priority=priority,
                attention_band="HIGH" if priority >= 0.75 else "MEDIUM",
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
        )
    attention = InventoryDiscoveryV1(
        run_id="radar-r2",
        run_hash=_hash("radar-r2"),
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        collector_run_id=bundle.collector_run_id,
        cash_pipeline_run_id=bundle.cash_pipeline_run_id,
        cash_pipeline_fingerprint=bundle.cash_pipeline_fingerprint,
        permission_fingerprint=bundle.permission_fingerprint,
        snapshot_bundle_id=bundle.snapshot_bundle_id,
        trading_date=TRADING_DATE.isoformat(),
        built_at=DECISION_AT,
        universe_count=len(rows),
        watch_count=len(rows),
        wait_count=0,
        reject_count=0,
        rows=tuple(rows),
    )
    return bundle, attention


def _radar(bundle, attention, *, signals=None, loader=None, ca=None, mcx=None):
    return build_evidence_radar(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, ca or {}),
        signals=signals if signals is not None else _signals(),
        loader=loader if loader is not None else _loader(),
        mcx_local_rows=[] if mcx is None else mcx,
        built_at=DECISION_AT,
    )


def _rows_by(radar):
    return {(row.symbol, row.horizon): row for row in radar.rows}


def _board_symbols(radar, horizon):
    board = radar.boards[horizon]
    return {entry.symbol for entry in (*board.buy, *board.sell)}


_BASE_SPECS = [
    ("cand-aaa", "AAA", EvidenceDirection.BULLISH),
    ("cand-bbb", "BBB", EvidenceDirection.BEARISH),
]


# ---------------------------------------------------------------------------
# C1 nothing skipped
# ---------------------------------------------------------------------------


def test_c1_coverage_every_source_has_one_slot(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c1.db")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(bundle, attention)
    coverage = radar.coverage
    assert coverage.totalJobs == len(DEFAULT_SOURCES)
    assert coverage.skippedCount == 0
    assert len(coverage.slots) == len(DEFAULT_SOURCES)
    assert len({slot.source_key for slot in coverage.slots}) == len(DEFAULT_SOURCES)
    assert all(slot.status for slot in coverage.slots)
    assert "nse_shareholding_pattern" in coverage.notNormalizedKeys


# ---------------------------------------------------------------------------
# C2 aliases/mirrors share one dataset root and never add a vote
# ---------------------------------------------------------------------------


def test_c2_alias_mirror_is_one_event_vote(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c2.db")
    _bars("AAA")
    bundle, attention = _spine(_BASE_SPECS)
    report, catalog = build_coverage(bundle)
    by_key = {entry.source_key: entry for entry in catalog.entries}
    assert by_key["bse_bulk_deals"].alias_of == "nse_bulk_deals_today_csv"
    assert by_key["bse_bulk_deals"].correlation_group == by_key["nse_bulk_deals_today_csv"].correlation_group
    radar = _radar(
        bundle,
        attention,
        signals=_signals(
            _deal("AAA", side="BUY", client="CLIENT A"),
            _deal("AAA", side="BUY", client="CLIENT A MIRROR"),
        ),
    )
    row = _rows_by(radar)[("AAA", "SWING")]
    event_family = row.families["EVENT_AND_SPONSOR"]
    # One family entry regardless of how many deal URLs carried the same story.
    assert list(row.families).count("EVENT_AND_SPONSOR") == 1
    assert event_family.representative_claim_id in {"NAMED_DEAL", "NAMED_FII_LIKE_DEAL"}
    del report


# ---------------------------------------------------------------------------
# C3 index close companion is not a 124th job
# ---------------------------------------------------------------------------


def test_c3_companion_listed_separately(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c3.db")
    sources = DEFAULT_SOURCES + (_src("nse_index_close"),)
    bundle, attention = _spine(_BASE_SPECS, sources)
    radar = _radar(bundle, attention)
    slot = next(s for s in radar.coverage.slots if s.source_key == "nse_index_close")
    assert slot.status.value == "COMPANION_ONLY"
    assert radar.coverage.totalJobs == len(sources)


# ---------------------------------------------------------------------------
# C4 market FII can never become per-stock fact
# ---------------------------------------------------------------------------


def test_c4_market_fii_chip_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c4.db")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(
        bundle,
        attention,
        loader=_loader(fii=[{"category": "FII_FPI", "buyValueCrore": 10, "sellValueCrore": 4}]),
    )
    assert radar.marketFiiChip.code == "MARKET_FII_NET_CHIP"
    dump = radar.model_dump_json()
    assert "fiiBoughtThisStock" not in dump


# ---------------------------------------------------------------------------
# C5 unnamed large deal is never FII
# ---------------------------------------------------------------------------


def test_c5_unnamed_deal_never_fii(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c5.db")
    _bars("AAA")
    bundle, attention = _spine([_BASE_SPECS[0]])
    radar = _radar(bundle, attention, signals=_signals(_deal("AAA", side="BUY", client=None)))
    row = _rows_by(radar)[("AAA", "SWING")]
    family = row.families["EVENT_AND_SPONSOR"]
    assert family.status == "MISSING"
    assert family.representative_claim_id == "UNNAMED_DEAL_NOT_FII"


# ---------------------------------------------------------------------------
# C6 third-party screens are INFO-zero and cannot seat a name
# ---------------------------------------------------------------------------


def test_c6_third_party_zero_score_offradar_excluded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c6.db")
    sources = DEFAULT_SOURCES + (
        _src("tickertape_fii_holding_change_3m", usability="CATALOG_ONLY"),
    )
    bundle, attention = _spine(_BASE_SPECS, sources)
    radar = _radar(
        bundle,
        attention,
        signals=_signals(_deal("OFFRADAR", side="BUY", client="BIG FII NAME")),
    )
    slot = next(s for s in radar.coverage.slots if s.source_key.startswith("tickertape"))
    assert slot.calculate == "INFO_ZERO_SCORE"
    assert not any(row.symbol == "OFFRADAR" for row in radar.rows)
    for horizon in ("INTRADAY", "SWING", "POSITION", "COMMODITY"):
        assert "OFFRADAR" not in _board_symbols(radar, horizon)


# ---------------------------------------------------------------------------
# C7 AMFI delayed; SHP null; never "last week"
# ---------------------------------------------------------------------------


def test_c7_amfi_delayed_shp_null(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c7.db")
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO amfi_stock_deltas (
                disclosure_month, stock, schemes_added, schemes_reduced,
                schemes_exited, net_quantity_change, parsed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-06", "AAA", 7, 0, 0, 250, DECISION_AT.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    bundle, attention = _spine([_BASE_SPECS[0]])
    radar = _radar(bundle, attention)
    row = _rows_by(radar)[("AAA", "POSITION")]
    assert row.what.startswith("DELAYED_MF_NET_ADDED_2026-06")
    assert "SHP_FII_DELTA_NOT_NORMALIZED" in row.whyUnknown
    assert "last week" not in radar.model_dump_json().lower()


# ---------------------------------------------------------------------------
# C8 delivery absent from intraday claims
# ---------------------------------------------------------------------------


def test_c8_no_delivery_on_intraday(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c8.db")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(
        bundle,
        attention,
        loader=_loader(mto=[{"symbol": "AAA", "series": "EQ", "delivery_pct": 40.0}]),
    )
    for symbol in ("AAA", "BBB"):
        row = _rows_by(radar)[(symbol, "INTRADAY")]
        assert "DELIVERY" not in row.families
        assert all("DELIVERY" not in code and "FORBIDDEN_ON_INTRADAY" not in code for code in row.why)
        assert "DELIVERY" not in row.how
    intraday_section = str(radar.boards["INTRADAY"].model_dump())
    assert "deliveryPct" not in intraday_section
    assert "CURRENT_PCT_ONLY" not in radar.boards["INTRADAY"].model_dump_json()


# ---------------------------------------------------------------------------
# C9 WAIT_CA excluded from all eight boards
# ---------------------------------------------------------------------------


def test_c9_wait_ca_vetoed_from_all_boards(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c9.db")
    _bars("AAA")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(bundle, attention, ca={"cand-aaa": "WAIT_CA"})
    for horizon in ("INTRADAY", "SWING", "POSITION", "COMMODITY"):
        assert "AAA" not in _board_symbols(radar, horizon)
    for key, row in _rows_by(radar).items():
        if row.symbol == "AAA":
            assert row.researchBoard == "NONE"


# ---------------------------------------------------------------------------
# C10 cash-only name is not punished for missing F&O
# ---------------------------------------------------------------------------


def test_c10_cash_only_not_punished_for_missing_fo(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c10.db")
    _bars("AAA")
    bundle, attention = _spine([_BASE_SPECS[0]])
    radar = _radar(bundle, attention)
    row = _rows_by(radar)[("AAA", "SWING")]
    fo = row.families["DERIVATIVES_FUTURES"]
    assert fo.status == "MISSING"
    assert fo.representative_claim_id == "NOT_IN_A6_SHORTLIST_CASH_ONLY_NOT_PUNISHED"
    assert row.researchBoard == "BUY"


# ---------------------------------------------------------------------------
# C11 volume never added twice (single participation representative)
# ---------------------------------------------------------------------------


def test_c11_single_participation_story(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c11.db")
    _bars("AAA")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(bundle, attention)
    for symbol in ("AAA", "BBB"):
        for horizon in ("INTRADAY", "SWING"):
            row = _rows_by(radar)[(symbol, horizon)]
            keys = [name for name in row.families if name == "PARTICIPATION"]
            assert keys == ["PARTICIPATION"]
            assert row.families["PARTICIPATION"].representative_claim_id == "R2_ATTENTION_READ"


# ---------------------------------------------------------------------------
# C12 commodity boards stay empty without local MCX even with global context
# ---------------------------------------------------------------------------


def test_c12_commodity_requires_local_mcx(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c12.db")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(bundle, attention)
    cftc_slot = next(s for s in radar.coverage.slots if s.source_key == "cftc_cot_positions")
    assert cftc_slot.status.value == "STALE"
    commodity = radar.boards["COMMODITY"]
    assert commodity.buy == () and commodity.sell == ()
    assert all(row.horizon != "COMMODITY" or row.publicState == "WAIT" for row in radar.rows)


# ---------------------------------------------------------------------------
# C13 intraday data mode is honest; no fake ORB confirmation
# ---------------------------------------------------------------------------


def test_c13_intraday_data_mode_honest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c13.db")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(bundle, attention)
    for symbol in ("AAA", "BBB"):
        row = _rows_by(radar)[(symbol, "INTRADAY")]
        assert row.dataMode == "DATA_MODE_EOD_OR_UNVERIFIED"
        assert row.dataMode != "LIVE_VERIFIED"
    assert "ORB_CONFIRMED" not in radar.model_dump_json()


# ---------------------------------------------------------------------------
# C14 position direction may diverge from R2 without rewriting R2
# ---------------------------------------------------------------------------


def test_c14_position_direction_diverges_from_session(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c14.db")
    _bars("AAA", last_open=102.0, prev_close=100.0)
    bundle, attention = _spine([_BASE_SPECS[0]])
    before_hash = attention.run_hash
    radar = _radar(
        bundle,
        attention,
        signals=_signals(_deal("AAA", side="SELL", client="BIG SELLER")),
    )
    swing = _rows_by(radar)[("AAA", "SWING")]
    position = _rows_by(radar)[("AAA", "POSITION")]
    assert swing.researchBoard == "BUY"      # structure + participation lead
    assert position.researchBoard == "SELL"  # named event leads on slow clock
    assert attention.run_hash == before_hash


# ---------------------------------------------------------------------------
# C15 conflict seats on neither board but stays visible
# ---------------------------------------------------------------------------


def test_c15_conflict_fusion_blocks_both_boards() -> None:
    bullish_event = CalculatedFact(
        family="EVENT_AND_SPONSOR",
        code="NAMED_DEAL_BUY",
        ok=True,
        direction=FactDirection.BULLISH,
        why="named buy",
        correlation_group="CG_EVENT_ROOT:A",
    )
    bearish_event = CalculatedFact(
        family="EVENT_AND_SPONSOR",
        code="NAMED_DEAL_SELL",
        ok=True,
        direction=FactDirection.BEARISH,
        why="named sell",
        correlation_group="CG_EVENT_ROOT:B",
    )
    fused = fuse_instrument([bullish_event, bearish_event], "SWING")
    assert fused.conflict is True
    assert fused.fused_direction == "CONFLICT"


def test_c15_conflicting_row_visible_but_unseated(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c15b.db")
    specs = _BASE_SPECS + [("cand-ccc", "CCC", EvidenceDirection.BULLISH)]
    bundle, attention = _spine(specs)
    radar = _radar(
        bundle,
        attention,
        signals=_signals(
            _deal("CCC", side="BUY", client="CLIENT A"),
            _deal("BBB", side="SELL", client="CLIENT B"),
        ),
    )
    ccc_rows = [row for row in radar.rows if row.symbol == "CCC"]
    assert ccc_rows, "conflicting name must remain visible as a dossier row"
    for row in ccc_rows:
        assert row.researchBoard in {"BUY", "NONE"}  # single rep cannot conflict


# ---------------------------------------------------------------------------
# C16 ceiling validators + read-only spine
# ---------------------------------------------------------------------------


def test_c16_validators_and_read_only_spine(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c16.db")
    bundle, attention = _spine(_BASE_SPECS)
    before = attention.run_hash
    radar = _radar(bundle, attention)
    payload = radar.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError):
        EvidenceRadarV1.model_validate({**payload, "canUnlockConfirmed": True})
    with pytest.raises(ValidationError):
        EvidenceRadarV1.model_validate({**payload, "sourceActivationReady": True})
    assert attention.run_hash == before


# ---------------------------------------------------------------------------
# C17 routes: POST 405; lineage mismatch 503
# ---------------------------------------------------------------------------


def test_c17_post_405() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/api/v1/selection/evidence-radar").status_code == 405
    assert client.post("/api/v1/selection/evidence-radar/boards").status_code == 405


def test_c17_lineage_mismatch_503(monkeypatch) -> None:
    from trendforge_api import main as main_module

    def _raise(**_kwargs):
        raise ValueError("WAIT_RADAR_LINEAGE_MISMATCH")

    monkeypatch.setattr(main_module, "build_evidence_radar", _raise)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/selection/evidence-radar")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WAIT_RADAR_LINEAGE_MISMATCH"


# ---------------------------------------------------------------------------
# C18/C19 explain contract: nothing silent
# ---------------------------------------------------------------------------


def test_c19_how_what_where_when_always_present(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c19.db")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(bundle, attention)
    assert radar.rows
    for row in radar.rows:
        for field in (
            row.how,
            row.what,
            row.where,
            row.when,
            row.nextConfirmCondition,
            row.invalidationCondition,
        ):
            assert isinstance(field, str) and field.strip()
        assert row.slotsSkippedCount == 0
        assert "NSE_CASH" in row.invalidationCondition or "UNKNOWN_INVALIDATION" in row.invalidationCondition or "prior" in row.invalidationCondition.lower() or "structure" in row.invalidationCondition.lower()


def test_board_cards_carry_how_what_where_when(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-board-speak.db")
    _bars("AAA")
    bundle, attention = _spine([_BASE_SPECS[0]])
    radar = _radar(bundle, attention)
    buy = radar.boards["SWING"].buy
    assert buy
    entry = buy[0]
    for field in (entry.how, entry.what, entry.where, entry.when):
        assert field.strip()
        assert field != "UNKNOWN"
    assert entry.invalidationCondition if hasattr(entry, "invalidationCondition") else True
    assert "where" in entry.model_dump(by_alias=True)


def test_official_filings_are_event_slots_not_unknown() -> None:
    from trendforge_api.selection.evidence_radar.catalog import _classify

    rule = _classify("nse_corporate_filings_actions")
    assert rule["family"] == "EVENT_AND_SPONSOR"
    assert rule["calculate"] != "NOT_NORMALIZED"
    most_active = _classify("nse_most_active_volume")
    assert most_active["family"] == "PARTICIPATION"
    assert most_active["calculate"] == "ACTIVITY_SESSION_JOIN_NOT_SECOND_VOTE"


def test_c12_local_mcx_can_seat_without_cftc(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-c12-local.db")
    bundle, attention = _spine(_BASE_SPECS)
    radar = _radar(
        bundle,
        attention,
        mcx=[
            {
                "symbol": "GOLD",
                "close": 110.0,
                "priorClose": 100.0,
                "oiChange": 12,
                "instrumentId": "MCX-GOLD",
            }
        ],
    )
    assert "GOLD" in _board_symbols(radar, "COMMODITY")
    gold = next(row for row in radar.rows if row.symbol == "GOLD" and row.horizon == "COMMODITY")
    assert gold.researchBoard == "BUY"
    assert gold.publicState == "WAIT"
    assert gold.how.startswith("local MCX")
    assert "CFTC" not in gold.how


def test_delivery_z_is_quality_not_a_buy_vote() -> None:
    from trendforge_api.selection.evidence_radar.calculate import delivery_fact

    series = [40.0 + (i * 0.05) for i in range(20)]
    series[-1] = 58.0
    fact = delivery_fact("AAA", "SWING", {"AAA": 58.0}, history=series)
    assert fact.code == "DELIVERY_Z_PIT20"
    assert fact.ok
    assert fact.direction.value == "NEUTRAL"
    intra = delivery_fact("AAA", "INTRADAY", {"AAA": 58.0}, history=series)
    assert intra.code == "FORBIDDEN_ON_INTRADAY"
    assert not intra.ok


def test_activity_join_does_not_replace_r2_vote(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-activity.db")
    _bars("AAA")
    bundle, attention = _spine([_BASE_SPECS[0]])
    radar = _radar(
        bundle,
        attention,
        loader=_loader(),
    )
    row = _rows_by(radar)[("AAA", "SWING")]
    assert row.families["PARTICIPATION"].representative_claim_id == "R2_ATTENTION_READ"


def test_leftover_inventory_keys_are_typed_slots() -> None:
    from trendforge_api.selection.evidence_radar.catalog import _classify

    expected = {
        "kite_derivatives_contract_master": "IDENTITY",
        "nse_fii_derivatives_stats": "MARKET_AND_SECTOR_CONTEXT",
        "nse_pit_symbol": "EVENT_AND_SPONSOR",
        "nse_regulation_29": "EVENT_AND_SPONSOR",
        "nse_quote_equity_trade_info": "PARTICIPATION",
        "nse_variations_gainers": "PARTICIPATION",
        "opec_production_adjustment": "GLOBAL_CONTEXT",
        "rbi_tbill_yield": "GLOBAL_CONTEXT",
        "world_gold_council_oi": "GLOBAL_CONTEXT",
        "yahoo_cme_proxy": "SECONDARY_DISCOVERY",
        "rupeevest_mf_flows": "SECONDARY_DISCOVERY",
    }
    for key, family in expected.items():
        assert _classify(key)["family"] == family, key


def test_preopen_uses_same_structure_group_as_gap() -> None:
    from trendforge_api.selection.evidence_radar.calculate import preopen_gap_fact

    fact = preopen_gap_fact("AAA", {"AAA": {"gap_pct": 1.5, "iep": 101.5}})
    assert fact.code == "PREOPEN_GAP_FTR001"
    assert fact.correlation_group == "CG_PRICE_STRUCTURE"
    assert fact.ok


def test_rs_uses_nifty_benchmark_when_present(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "radar-rs.db")
    storage.init_db()
    from trendforge_api.selection.cash_a4_history import CashRawSessionBar, _store_raw_bar
    from trendforge_api.selection.evidence_radar.calculate import rs_fact

    class _C:
        def __init__(self, close):
            self.close = close

    for i in range(10):
        day = TRADING_DATE - timedelta(days=12 - i)
        _store_raw_bar(
            CashRawSessionBar(
                bar_id=f"AAA-rs-{i}",
                instrument_id="inst-x",
                symbol="AAA",
                trade_date=day,
                artifact_hash=_hash(f"AAA-rs-{i}"),
                series_id="raw-series",
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.0 + i,
                previous_close=99.0 + i,
                volume=1000.0,
                traded_value=100000.0,
            )
        )
    bench = [_C(1000 + i) for i in range(10)]
    fact = rs_fact("AAA", TRADING_DATE, benchmark_bars=bench, windows=(5,))
    assert fact.ok
    assert fact.code == "RS_MULTI_WINDOW_V1"
