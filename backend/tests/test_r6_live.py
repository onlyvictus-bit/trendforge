"""File A R6 live enrichment stickers + honest source contract tests (T1-T12)."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from trendforge_api import storage
from trendforge_api.main import app
from trendforge_api.selection.attention_order import (
    AttentionRowV1,
    InventoryDiscoveryV1,
)
from trendforge_api.selection.cash_a4_history import (
    CashRawSessionBar,
    _store_raw_bar,
)
from trendforge_api.selection.contracts import (
    EvidenceDirection,
    InstrumentIdentity,
    NormalizedFact,
    PointInTimeLineage,
    SelectionState,
)
from trendforge_api.fii_stock_signals import (
    FIIStockSignalsSnapshot,
    LargeDealSignal,
)
from trendforge_api.selection.inventory_source_bundle import (
    InventorySourceBundleV1,
    StockEvidenceRecordV1,
)
from trendforge_api.selection.r14_live import R14CaJoinBatchV1, R14CaJoinRowV1
from trendforge_api.selection.r6_live import (
    GAP_ALIGNED_BONUS,
    MF_DELAYED_BONUS,
    NAMED_DEAL_BONUS,
    STICKER_BONUS_CAP,
    build_r6_enrichment,
)

TRADING_DATE = date(2026, 8, 14)
DECISION_AT = datetime(2026, 8, 14, 17, 0, tzinfo=UTC)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _stock(
    candidate_id: str, symbol: str, direction: EvidenceDirection
) -> StockEvidenceRecordV1:
    instrument = InstrumentIdentity.create(
        exchange="NSE",
        segment="EQ",
        symbol=symbol,
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
        business_keys={
            "symbol": instrument.symbol,
            "trade_date": TRADING_DATE.isoformat(),
        },
        data_date=TRADING_DATE,
        lineage=lineage,
        quality_state="STRUCTURED_OK",
        payload={"symbol": instrument.symbol, "close": 110.0},
    )
    return StockEvidenceRecordV1(
        candidate_id=candidate_id,
        symbol=symbol,
        instrument_id=instrument.instrument_id,
        fact_id=fact.fact_id,
        public_state=SelectionState.WATCH,
        evidence_direction=direction,
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


def _spine(specs):
    """specs: list of (candidate_id, symbol, direction). Returns (bundle, attention)."""
    stocks = [_stock(*spec) for spec in specs]
    bundle = InventorySourceBundleV1(
        bundle_id="r1-bundle",
        bundle_hash=_hash("r1"),
        collector_run_id="collector-r6",
        cash_pipeline_run_id="cash-r6",
        cash_pipeline_fingerprint=_hash("pipeline"),
        permission_fingerprint=_hash("permission"),
        snapshot_bundle_id="snapshot-r6",
        trading_date=TRADING_DATE,
        built_at=DECISION_AT,
        registry_sha256=_hash("registry"),
        source_contract_count=0,
        stock_record_count=len(stocks),
        stage_states={"C1": "COMPLETED"},
        source_records=(),
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
        universe_count=len(rows),
        watch_count=len(rows),
        wait_count=0,
        reject_count=0,
        rows=tuple(rows),
    )
    return bundle, attention


def _r14(bundle, attention, ca_by_candidate):
    rows = []
    for row in attention.rows:
        ca_state = ca_by_candidate.get(row.candidate_id, "NONE")
        join_status = "JOINED" if ca_state == "ADJUSTED" else "NONE"
        if ca_state == "WAIT_CA":
            join_status = "WAIT_DETAILS"
        rows.append(
            R14CaJoinRowV1(
                candidate_id=row.candidate_id,
                symbol=row.symbol,
                display_order=row.display_order,
                r2_public_state=row.public_state,
                join_status=join_status,
                ca_state=ca_state,
                raw_series_id="raw-series",
                identity_continuity="SAME_INSTRUMENT",
                factor_version="r14-ca-factor-fixture" if ca_state == "ADJUSTED" else None,
                adjusted_series_id="adj-series" if ca_state == "ADJUSTED" else None,
                why_wait=("R14_LIVE_WAIT_CEILING",),
            )
        )
    return R14CaJoinBatchV1(
        run_id="r14-run",
        run_hash=_hash("r14"),
        r1_bundle_id=bundle.bundle_id,
        r1_bundle_hash=bundle.bundle_hash,
        r2_run_id=attention.run_id,
        r2_run_hash=attention.run_hash,
        r4_run_id="r4-run",
        r4_run_hash=_hash("r4"),
        collector_run_id=bundle.collector_run_id,
        cash_pipeline_run_id=bundle.cash_pipeline_run_id,
        permission_fingerprint=bundle.permission_fingerprint,
        trading_date=TRADING_DATE.isoformat(),
        decision_at=DECISION_AT,
        universe_count=len(rows),
        joined_count=sum(r.join_status == "JOINED" for r in rows),
        wait_ca_count=sum(r.ca_state == "WAIT_CA" for r in rows),
        conflict_count=sum(r.join_status == "CONFLICT" for r in rows),
        none_count=sum(r.join_status == "NONE" for r in rows),
        rows=tuple(rows),
    )


def _loader(*, fii=None, mto=None):
    def _load(key):
        if key == "nse_fii_dii" and fii is not None:
            return {
                "parserState": "PARSED_STRUCTURED",
                "dataDate": TRADING_DATE.isoformat(),
                "output": {"rows": fii},
            }
        if key == "nse_mto_delivery" and mto is not None:
            return {
                "parserState": "PARSED_STRUCTURED",
                "dataDate": TRADING_DATE.isoformat(),
                "output": {"rows": mto},
            }
        return None

    return _load


def _signals(*deals) -> FIIStockSignalsSnapshot:
    return FIIStockSignalsSnapshot(generated_at=DECISION_AT, large_deals=list(deals))


def _deal(symbol, side="BUY", client=None, deal_date="2026-08-12"):
    return LargeDealSignal(
        symbol=symbol,
        side=side,
        client=client,
        quantity=100000,
        price=100.0,
        value=10000000.0,
        deal_type="BULK",
        date=deal_date,
        source_key="nse_bulk_deals_today_csv",
    )


def _bars(symbol: str, *, last_open: float = 102.0, prev_close: float = 100.0) -> None:
    _store_raw_bar(
        CashRawSessionBar(
            bar_id=f"{symbol}-b1",
            instrument_id="inst-x",
            symbol=symbol,
            trade_date=TRADING_DATE - timedelta(days=2),
            artifact_hash=_hash(f"{symbol}-b1"),
            series_id="raw-series",
            open=prev_close,
            high=prev_close + 1,
            low=prev_close - 1,
            close=prev_close,
            previous_close=prev_close,
            volume=1000.0,
            traded_value=100000.0,
        )
    )
    _store_raw_bar(
        CashRawSessionBar(
            bar_id=f"{symbol}-b2",
            instrument_id="inst-x",
            symbol=symbol,
            trade_date=TRADING_DATE,
            artifact_hash=_hash(f"{symbol}-b2"),
            series_id="raw-series",
            open=last_open,
            high=last_open + 1,
            low=last_open - 2,
            close=last_open + 0.5,
            previous_close=prev_close,
            volume=1200.0,
            traded_value=120000.0,
        )
    )


# ---------------------------------------------------------------------------
# T1 market FII chip can never become a per-stock fact
# ---------------------------------------------------------------------------


def test_t1_market_fii_never_names_stocks(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t1.db")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    batch = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {}),
        signals=_signals(),
        loader=_loader(
            fii=[{"category": "FII_FPI", "buyValueCrore": 3000, "sellValueCrore": 500}]
        ),
        built_at=DECISION_AT,
    )
    assert batch.market_fii.net_crore == pytest.approx(2500.0)
    assert batch.market_fii.scope == "MARKET_WIDE_NOT_PER_STOCK"
    dump_keys = set(batch.rows[0].model_dump(by_alias=True))
    assert "fiiBoughtThisStock" not in dump_keys
    assert "marketFiiNet" not in dump_keys
    assert all(row.shp_fii_delta is None for row in batch.rows)


# ---------------------------------------------------------------------------
# T2 unnamed large deal is never an FII buy and never earns a tag
# ---------------------------------------------------------------------------


def test_t2_unnamed_deal_not_tagged(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t2.db")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    base = attention.rows[0].attention_priority
    batch = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {}),
        signals=_signals(_deal("AAA", side="BUY", client=None)),
        loader=_loader(),
        built_at=DECISION_AT,
    )
    row = batch.rows[0]
    assert row.deal_summary is not None and "UNNAMED_DEAL" in row.deal_summary
    assert row.deal_tag is None
    assert "NAMED_DEAL" not in row.tags
    assert row.display_score == pytest.approx(base)


# ---------------------------------------------------------------------------
# gap sticker gating (R14 CA authority)
# ---------------------------------------------------------------------------


def test_gap_computed_when_adjusted_and_unknown_when_wait_ca(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-gap.db")
    _bars("AAA", last_open=102.0, prev_close=100.0)
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])

    joined = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {"cand-aaa": "ADJUSTED"}),
        signals=_signals(),
        loader=_loader(),
        built_at=DECISION_AT,
    )
    assert joined.rows[0].gap_pct == pytest.approx(2.0)
    assert joined.rows[0].gap_status == "CURRENT_ADJUSTED_SAFE"

    blocked = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {"cand-aaa": "WAIT_CA"}),
        signals=_signals(),
        loader=_loader(),
        built_at=DECISION_AT,
    )
    assert blocked.rows[0].gap_pct is None
    assert blocked.rows[0].gap_status == "UNKNOWN_WAIT_CA"
    assert "GAP_UNKNOWN_WAIT_CA" in blocked.rows[0].why_unknown


# ---------------------------------------------------------------------------
# T4 SHP stays null; AMFI labelled delayed month, never "last week"
# ---------------------------------------------------------------------------


def test_t4_shp_null_amfi_delayed_label(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t4.db")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    batch = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {"cand-aaa": "ADJUSTED"}),
        signals=_signals(_deal("AAA", side="BUY", client="SOME FUND FII LTD")),
        loader=_loader(mto=[{"symbol": "AAA", "series": "EQ", "delivery_pct": 41.0}]),
        built_at=DECISION_AT,
    )
    row = batch.rows[0]
    assert row.shp_fii_delta is None
    assert "SHP_FII_DELTA_NOT_NORMALIZED" in row.why_unknown
    # model_copy bypasses validators, so re-validate through the model itself.
    payload = row.model_dump(by_alias=True)
    payload["shpFiiDelta"] = 1.25
    with pytest.raises(ValidationError):
        type(row).model_validate(payload)
    blob = batch.model_dump_json()
    assert "last week" not in blob.lower()
    # Named client carrying FII/FPI is still a named deal, not the daily tape.
    assert row.deal_tag == "NAMED_FII_LIKE_DEAL"


# ---------------------------------------------------------------------------
# T6 cash-only name missing FO is not punished
# ---------------------------------------------------------------------------


def test_t6_cash_only_missing_fo_not_punished(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t6.db")
    bundle, attention = _spine(
        [
            ("cand-aaa", "AAA", EvidenceDirection.BULLISH),
            ("cand-bbb", "BBB", EvidenceDirection.BULLISH),
        ]
    )

    class _Fo:
        rows = ()

    batch = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {}),
        signals=_signals(),
        loader=_loader(),
        fo=_Fo(),
        built_at=DECISION_AT,
    )
    aaa, bbb = batch.rows[0], batch.rows[1]
    assert aaa.fo_package == "NOT_IN_A6_SHORTLIST"
    assert bbb.fo_package == "NOT_IN_A6_SHORTLIST"
    # Missing FO changes no score: sticker delta over the R2 base is equal.
    assert (
        round(aaa.display_score - aaa.attention_priority, 6)
        == round(bbb.display_score - bbb.attention_priority, 6)
    )


# ---------------------------------------------------------------------------
# T7 volume is never re-added on top of R2 priority; bonus cap holds
# ---------------------------------------------------------------------------


def test_t7_score_formula_and_cap(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t7.db")
    _bars("AAA")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    base = attention.rows[0].attention_priority
    batch = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {"cand-aaa": "ADJUSTED"}),
        signals=_signals(_deal("AAA", side="BUY", client="MUTUAL FUND CO")),
        loader=_loader(mto=[{"symbol": "AAA", "series": "EQ", "delivery_pct": 55.0}]),
        built_at=DECISION_AT,
    )
    row = batch.rows[0]
    # GAP_ALIGNED + NAMED_DEAL fire; no AMFI row exists so MF does not.
    expected_bonus = min(STICKER_BONUS_CAP, GAP_ALIGNED_BONUS + NAMED_DEAL_BONUS)
    assert row.tags == ("GAP_ALIGNED", "NAMED_DEAL")
    assert row.delivery_status == "CURRENT_PCT_FACT"
    assert row.display_score == pytest.approx(round(base + expected_bonus, 6))
    # Volume/turnover percentiles are inside the R2 base only.
    assert not any(tag.upper().startswith("VOLUME") for tag in row.tags)

    # With AMFI aligned too, total bonus is capped at STICKER_BONUS_CAP.
    storage.init_db()
    conn = storage.connect()
    try:
        conn.execute(
            """
            INSERT INTO amfi_stock_deltas (
                disclosure_month, stock, isin, schemes_added, schemes_reduced,
                schemes_exited, net_quantity_change, parsed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026-06", "AAA", "INE000A01001", 5, 0, 0, 100, DECISION_AT.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    batch_with_mf = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {"cand-aaa": "ADJUSTED"}),
        signals=_signals(_deal("AAA", side="BUY", client="MUTUAL FUND CO")),
        loader=_loader(),
        built_at=DECISION_AT,
    )
    mf_row = batch_with_mf.rows[0]
    assert mf_row.mf_delta == "NET_ADDED_2026-06"
    assert "MF_DELAYED" in mf_row.tags
    max_bonus = GAP_ALIGNED_BONUS + NAMED_DEAL_BONUS + MF_DELAYED_BONUS
    if max_bonus > STICKER_BONUS_CAP:
        assert mf_row.display_score == pytest.approx(round(base + STICKER_BONUS_CAP, 6))
    else:
        assert mf_row.display_score == pytest.approx(round(base + max_bonus, 6))


# ---------------------------------------------------------------------------
# T8 ceiling validators: no CONFIRMED, no unlock, no activation
# ---------------------------------------------------------------------------


def test_t8_ceiling_validators(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t8.db")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    batch = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {}),
        signals=_signals(),
        loader=_loader(),
        built_at=DECISION_AT,
    )
    assert batch.can_unlock_confirmed is False
    assert batch.source_activation_ready is False
    assert batch.state_ceiling is not None and batch.acceptance_ceiling.startswith("RESEARCH")
    payload = batch.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValidationError):
        type(batch).model_validate({**payload, "canUnlockConfirmed": True})
    with pytest.raises(ValidationError):
        type(batch).model_validate({**payload, "sourceActivationReady": True})
    rows = [dict(item) for item in payload["rows"]]
    rows[0]["researchState"] = "CONFIRMED"
    with pytest.raises(ValidationError):
        type(batch).model_validate({**payload, "rows": rows})


# ---------------------------------------------------------------------------
# T9 lineage mismatch raises WAIT_R6_LINEAGE_MISMATCH; route maps to 503
# ---------------------------------------------------------------------------


def test_t9_lineage_mismatch_value_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t9.db")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    stale_r14 = _r14(bundle, attention, {})
    stale_r14 = stale_r14.model_copy(update={"run_id": "older-r14"})
    from trendforge_api.selection import r6_live as r6_module

    monkeypatch.setattr(r6_module, "latest_attention_order", lambda: attention)
    monkeypatch.setattr(r6_module, "latest_inventory_source_bundle", lambda: bundle)
    monkeypatch.setattr(r6_module, "latest_r14_ca_join", lambda: None)
    with pytest.raises(ValueError, match="WAIT_R6_SPINE_NOT_READY"):
        build_r6_enrichment()

    mismatched = attention.model_copy(
        update={"r1_bundle_hash": _hash("different")}
    )
    with pytest.raises(ValueError, match="WAIT_R6_LINEAGE_MISMATCH"):
        build_r6_enrichment(
            bundle=bundle,
            attention=mismatched,
            r14=stale_r14,
            signals=_signals(),
            loader=_loader(),
            built_at=DECISION_AT,
        )


def test_t9_route_returns_503_on_lineage_mismatch(monkeypatch) -> None:
    from trendforge_api import main as main_module

    def _raise(**_kwargs):
        raise ValueError("WAIT_R6_LINEAGE_MISMATCH")

    monkeypatch.setattr(main_module, "build_r6_enrichment", _raise)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/selection/enrichment")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WAIT_R6_LINEAGE_MISMATCH"


# ---------------------------------------------------------------------------
# T10 POST is rejected (405) on both read-only routes
# ---------------------------------------------------------------------------


def test_t10_post_is_405() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/api/v1/selection/enrichment").status_code == 405
    assert client.post("/api/v1/selection/top10").status_code == 405


# ---------------------------------------------------------------------------
# T11 missing MTO means delivery UNKNOWN, never a volume proxy
# ---------------------------------------------------------------------------


def test_t11_missing_mto_delivery_unknown(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t11.db")
    _bars("AAA")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    batch = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {"cand-aaa": "ADJUSTED"}),
        signals=_signals(),
        loader=_loader(),  # no MTO last-good at all
        built_at=DECISION_AT,
    )
    row = batch.rows[0]
    assert row.delivery_pct is None
    assert row.delivery_status == "UNKNOWN_MISSING_SOURCE"
    assert "DELIVERY_SOURCE_MISSING" in row.why_unknown
    # Cash bars exist independently; delivery absence never fakes delivery.
    assert row.gap_pct is not None


# ---------------------------------------------------------------------------
# T12 building R6 never mutates or repersists the R2 spine
# ---------------------------------------------------------------------------


def test_t12_r2_spine_read_only(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "r6-t12.db")
    bundle, attention = _spine([("cand-aaa", "AAA", EvidenceDirection.BULLISH)])
    before_hash = attention.run_hash
    first = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {}),
        signals=_signals(),
        loader=_loader(),
        built_at=DECISION_AT,
    )
    second = build_r6_enrichment(
        bundle=bundle,
        attention=attention,
        r14=_r14(bundle, attention, {}),
        signals=_signals(),
        loader=_loader(),
        built_at=DECISION_AT,
    )
    assert attention.run_hash == before_hash
    assert attention.persisted is False
    assert first.run_hash == second.run_hash
    assert first.run_id == second.run_id
